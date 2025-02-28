from common.celery_app import celery_app, TASK_EXECUTION_TIME, TASK_FAILURE_COUNTER
from celery.utils.log import get_task_logger
from .models import (
    LoanRequest, LoanRequestStatus, LoanRequestError,
    Document
)
from typing import Dict, List
import aio_pika
import json
from datetime import datetime
import os
from decimal import Decimal

logger = get_task_logger(__name__)

@celery_app.task(
    name='loan_request.validate_application',
    bind=True,
    max_retries=3,
    default_retry_delay=30
)
def validate_application(self, request_data: Dict) -> Dict:
    """
    Validates the loan application data and required documents
    """
    try:
        # Convert dict to LoanRequest model for validation
        loan_request = LoanRequest(**request_data)
        
        # Initialize validation results
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate age
        age = (datetime.now() - loan_request.birth_date).days / 365.25
        if age < 18:
            validation_results["is_valid"] = False
            validation_results["errors"].append("Applicant must be at least 18 years old")
        elif age > 75:
            validation_results["warnings"].append("Age verification required")
        
        # Validate loan amount vs income
        annual_income = loan_request.monthly_income * Decimal('12')
        if loan_request.loan_amount > annual_income * Decimal('5'):
            validation_results["warnings"].append("Loan amount exceeds 5x annual income")
        
        # Validate debt-to-income ratio
        total_monthly_debt = loan_request.monthly_expenses
        for loan in loan_request.existing_loans:
            total_monthly_debt += loan.get('monthly_payment', Decimal('0'))
        
        dti_ratio = total_monthly_debt / loan_request.monthly_income
        if dti_ratio > Decimal('0.43'):
            validation_results["warnings"].append("DTI ratio exceeds 43%")
        
        return {
            "request_id": loan_request.request_id,
            "validation_results": validation_results,
            "status": (
                LoanRequestStatus.SUBMITTED if validation_results["is_valid"]
                else LoanRequestStatus.REJECTED
            )
        }
        
    except Exception as exc:
        logger.error(f"Validation failed for request {request_data.get('request_id')}: {str(exc)}")
        self.retry(exc=exc)

@celery_app.task(
    name='loan_request.process_documents',
    bind=True,
    max_retries=3
)
def process_documents(self, request_id: str, documents: List[Dict]) -> Dict:
    """
    Processes and validates submitted documents
    """
    try:
        required_documents = {
            "identity_proof": False,
            "income_proof": False,
            "tax_notice": False,
            "property_details": False
        }
        
        processed_docs = []
        
        for doc in documents:
            document = Document(**doc)
            
            # Validate document
            validation_result = validate_document(document)
            
            if validation_result["is_valid"]:
                required_documents[document.document_type] = True
            
            processed_docs.append({
                "document_id": document.document_id,
                "status": "VALIDATED" if validation_result["is_valid"] else "INVALID",
                "errors": validation_result.get("errors", [])
            })
        
        # Check if all required documents are present and valid
        all_documents_valid = all(required_documents.values())
        
        return {
            "request_id": request_id,
            "documents_processed": len(processed_docs),
            "documents_valid": all_documents_valid,
            "missing_documents": [
                doc_type for doc_type, is_valid in required_documents.items()
                if not is_valid
            ],
            "processed_documents": processed_docs
        }
        
    except Exception as exc:
        logger.error(f"Document processing failed for request {request_id}: {str(exc)}")
        self.retry(exc=exc)

@celery_app.task(name='loan_request.generate_summary')
def generate_summary(request_id: str, loan_request: Dict, validation_result: Dict) -> Dict:
    """
    Generates a summary of the loan request for further processing
    """
    try:
        # Calculate key metrics
        annual_income = Decimal(str(loan_request['monthly_income'])) * Decimal('12')
        loan_amount = Decimal(str(loan_request['loan_amount']))
        loan_to_income_ratio = loan_amount / annual_income
        
        return {
            "request_id": request_id,
            "summary": {
                "client_name": loan_request['client_name'],
                "loan_amount": float(loan_amount),
                "loan_duration_years": loan_request['loan_duration_years'],
                "annual_income": float(annual_income),
                "loan_to_income_ratio": float(loan_to_income_ratio),
                "property_type": loan_request['property_info']['type'],
                "property_value": float(loan_request['property_info'].get('estimated_value', 0)),
                "validation_status": validation_result['status']
            }
        }
    except Exception as e:
        logger.error(f"Summary generation failed for request {request_id}: {str(e)}")
        raise

def validate_document(document: Document) -> Dict:
    """
    Validates individual document
    """
    validation_result = {
        "is_valid": True,
        "errors": []
    }
    
    # Validate file size
    max_size = 10 * 1024 * 1024  # 10MB
    if document.file_size > max_size:
        validation_result["is_valid"] = False
        validation_result["errors"].append("File size exceeds maximum limit")
    
    # Validate mime type
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
    if document.mime_type not in allowed_types:
        validation_result["is_valid"] = False
        validation_result["errors"].append("Invalid file type")
    
    return validation_result
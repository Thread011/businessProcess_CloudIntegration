from common.celery_app import celery_app, TASK_LATENCY, TASK_FAILURE_COUNTER
from celery.utils.log import get_task_logger
from .models import (
    DecisionStatus, DecisionReason, DecisionResult,
    DecisionRequest, DecisionCriteria
)


from decimal import Decimal
import time
from typing import List
from functools import wraps

logger = get_task_logger(__name__)

def monitor_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        task_name = func.__name__
        try:
            result = func(*args, **kwargs)
            TASK_LATENCY.labels(task_name=task_name).observe(
                time.time() - start_time
            )
            return result
        except Exception as e:
            TASK_FAILURE_COUNTER.labels(task_name=task_name).inc()
            logger.error(f"Task {task_name} failed: {str(e)}")
            raise
    return wrapper

@celery_app.task(
    name='decision.evaluate_application',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
@monitor_task
def evaluate_application(self, decision_request: dict) -> dict:
    try:
        # Convert dict to DecisionRequest model
        request = DecisionRequest(**decision_request)
        app = request.application_summary
        criteria = request.criteria
        
        # Initialize reasons list
        reasons: List[DecisionReason] = []
        
        # Evaluate all criteria
        meets_credit_score = app.credit_score >= criteria.min_credit_score
        meets_dti = app.dti_ratio <= criteria.max_dti_ratio
        meets_property_value = (
            app.property_value >= 
            app.loan_amount * Decimal(str(criteria.min_property_value_ratio))
        )
        
        # Calculate annual loan payment (simplified)
        annual_interest_rate = Decimal('0.035')  # 3.5% fixed for example
        monthly_rate = annual_interest_rate / Decimal('12')
        num_payments = app.loan_duration_years * 12
        monthly_payment = app.loan_amount * (
            monthly_rate * (1 + monthly_rate)**num_payments
        ) / ((1 + monthly_rate)**num_payments - 1)
        annual_loan_payment = monthly_payment * Decimal('12')
        annual_income = app.monthly_income * Decimal('12')
        
        meets_income_ratio = (
            annual_loan_payment <= 
            annual_income * Decimal(str(criteria.max_loan_to_income_ratio))
        )
        
        # Collect failing reasons
        if not meets_credit_score:
            reasons.append(DecisionReason.CREDIT_SCORE_LOW)
        if not meets_dti:
            reasons.append(DecisionReason.DTI_RATIO_HIGH)
        if not meets_property_value:
            reasons.append(DecisionReason.PROPERTY_VALUE_INSUFFICIENT)
        if not meets_income_ratio:
            reasons.append(DecisionReason.INCOME_INSUFFICIENT)
            
        # Determine final status
        if not reasons:
            status = DecisionStatus.APPROVED
            reasons = [DecisionReason.ALL_CRITERIA_MET]
        elif len(reasons) == 1 and app.credit_score >= 600:
            status = DecisionStatus.NEEDS_REVIEW
            reasons.append(DecisionReason.MANUAL_REVIEW_REQUIRED)
        else:
            status = DecisionStatus.REJECTED
            
        # Create decision result
        result = DecisionResult(
            request_id=request.request_id,
            status=status,
            reasons=reasons,
            details={
                "credit_score_check": meets_credit_score,
                "dti_ratio_check": meets_dti,
                "property_value_check": meets_property_value,
                "income_ratio_check": meets_income_ratio,
                "monthly_payment": float(monthly_payment),
                "annual_loan_payment": float(annual_loan_payment),
                "interest_rate": float(annual_interest_rate * 100)  # Convert to percentage
            },
            proposed_rate=float(annual_interest_rate * 100)  # Add as top-level field
        )
        
        return result.dict()
        
    except Exception as exc:
        logger.error(f"Decision evaluation failed for request {decision_request['request_id']}: {str(exc)}")
        self.retry(exc=exc)
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from decimal import Decimal
import json

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class DecisionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ERROR = "ERROR"

class DecisionReason(str, Enum):
    CREDIT_SCORE_LOW = "CREDIT_SCORE_LOW"
    DTI_RATIO_HIGH = "DTI_RATIO_HIGH"
    PROPERTY_VALUE_INSUFFICIENT = "PROPERTY_VALUE_INSUFFICIENT"
    INCOME_INSUFFICIENT = "INCOME_INSUFFICIENT"
    ALL_CRITERIA_MET = "ALL_CRITERIA_MET"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

class LoanApplicationSummary(BaseModel):
    request_id: str
    client_name: str
    loan_amount: Decimal
    loan_duration_years: int
    property_value: Decimal
    monthly_income: Decimal
    monthly_expenses: Decimal
    credit_score: int
    dti_ratio: float
    property_assessment_result: str

class DecisionCriteria(BaseModel):
    min_credit_score: int = 650
    max_dti_ratio: float = 0.43
    min_property_value_ratio: float = 1.2  # Property value must be 120% of loan
    max_loan_to_income_ratio: float = 4.0  # Annual loan payment vs annual income

class DecisionRequest(BaseModel):
    request_id: str
    application_summary: LoanApplicationSummary
    criteria: Optional[DecisionCriteria] = Field(default_factory=DecisionCriteria)

class DecisionResult(BaseModel):
    request_id: str
    status: DecisionStatus
    reasons: List[DecisionReason]
    details: Dict[str, Any]
    decision_date: datetime = Field(default_factory=datetime.now)
    expiration_date: Optional[datetime] = None
    reviewer: Optional[str] = None
    proposed_rate: Optional[float] = None
    requirements: Optional[List[str]] = None
    notes: Optional[List[str]] = None
    
    @validator('expiration_date', always=True)
    def set_expiration_date(cls, v, values):
        if v is None and 'decision_date' in values:
            # Set expiration to 30 days from decision using timedelta
            return values['decision_date'] + timedelta(days=30)
        return v

    model_config = {
        'arbitrary_types_allowed': True
    }
    
    def dict(self, **kwargs):
        """Override dict method to handle datetime serialization"""
        result = super().dict(**kwargs)
        if 'decision_date' in result and isinstance(result['decision_date'], datetime):
            result['decision_date'] = result['decision_date'].isoformat()
        if 'expiration_date' in result and isinstance(result['expiration_date'], datetime):
            result['expiration_date'] = result['expiration_date'].isoformat()
        return result

class DecisionError(BaseModel):
    request_id: str
    error_code: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[dict] = None
    
    def dict(self, **kwargs):
        """Override dict method to handle datetime serialization"""
        result = super().dict(**kwargs)
        if 'timestamp' in result and isinstance(result['timestamp'], datetime):
            result['timestamp'] = result['timestamp'].isoformat()
        return result
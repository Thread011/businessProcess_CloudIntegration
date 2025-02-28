from pydantic import BaseModel, Field, validator
from decimal import Decimal
from typing import Optional
from datetime import datetime
from enum import Enum

class CreditRating(str, Enum):
    EXCELLENT = "EXCELLENT"  # 800-850
    VERY_GOOD = "VERY_GOOD"  # 740-799
    GOOD = "GOOD"           # 670-739
    FAIR = "FAIR"          # 580-669
    POOR = "POOR"          # 300-579

class CreditRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class CreditCheckRequest(BaseModel):
    request_id: str = Field(..., description="Unique identifier for the loan request")
    client_name: str
    monthly_income: Decimal = Field(..., ge=0)
    monthly_expenses: Decimal = Field(..., ge=0)
    existing_loans: Optional[Decimal] = Field(0, ge=0)
    employment_years: Optional[float] = Field(..., ge=0)
    
    @validator('monthly_expenses')
    def validate_expenses(cls, v, values):
        if 'monthly_income' in values and v >= values['monthly_income']:
            raise ValueError("Monthly expenses cannot be greater than or equal to monthly income")
        return v

class CreditScore(BaseModel):
    score: int = Field(..., ge=300, le=850)
    rating: CreditRating
    check_date: datetime = Field(default_factory=datetime.now)
    
    @validator('rating', pre=True)
    def set_rating(cls, v, values):
        if 'score' in values:
            score = values['score']
            if score >= 800:
                return CreditRating.EXCELLENT
            elif score >= 740:
                return CreditRating.VERY_GOOD
            elif score >= 670:
                return CreditRating.GOOD
            elif score >= 580:
                return CreditRating.FAIR
            else:
                return CreditRating.POOR
        return v

class CreditCheckResult(BaseModel):
    request_id: str
    credit_score: CreditScore
    dti_ratio: float = Field(..., ge=0, le=1)
    risk_level: CreditRiskLevel
    is_eligible: bool
    monthly_payment_capacity: Decimal
    evaluation_date: datetime = Field(default_factory=datetime.now)
    details: Optional[dict] = Field(default_factory=dict)
    
    @validator('risk_level', pre=True)
    def calculate_risk_level(cls, v, values):
        if 'dti_ratio' in values and 'credit_score' in values:
            dti = values['dti_ratio']
            score = values['credit_score'].score
            
            if score >= 700 and dti <= 0.35:
                return CreditRiskLevel.LOW
            elif score >= 600 and dti <= 0.43:
                return CreditRiskLevel.MEDIUM
            else:
                return CreditRiskLevel.HIGH
        return v
    
    @validator('is_eligible', pre=True)
    def determine_eligibility(cls, v, values):
        if 'risk_level' in values and 'dti_ratio' in values:
            return (values['risk_level'] != CreditRiskLevel.HIGH and 
                   values['dti_ratio'] <= 0.43)
        return v

class CreditCheckError(BaseModel):
    request_id: str
    error_code: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[dict] = None

# For tracking the status of credit check requests
class CreditCheckStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class CreditCheckStatusUpdate(BaseModel):
    request_id: str
    status: CreditCheckStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[dict] = None
    error: Optional[CreditCheckError] = None
from pydantic import BaseModel, Field, EmailStr, validator, constr
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from decimal import Decimal
import re

class LoanPurpose(str, Enum):
    PURCHASE = "PURCHASE"
    REFINANCE = "REFINANCE"
    RENOVATION = "RENOVATION"
    CONSTRUCTION = "CONSTRUCTION"

class PropertyType(str, Enum):
    HOUSE = "HOUSE"
    APARTMENT = "APARTMENT"
    COMMERCIAL = "COMMERCIAL"
    LAND = "LAND"

class LoanRequestStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VALIDATING = "VALIDATING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"

class Address(BaseModel):
    street: str
    city: str
    postal_code: str
    country: str = "France"
    
    @validator('postal_code')
    def validate_french_postal_code(cls, v):
        if not re.match(r'^\d{5}$', v):
            raise ValueError('Invalid French postal code format')
        return v

class EmploymentInfo(BaseModel):
    employer_name: str
    position: str
    years_employed: float = Field(..., ge=0)
    contract_type: str
    annual_income: Decimal = Field(..., ge=0)
    
    @validator('contract_type')
    def validate_contract_type(cls, v):
        valid_types = ['CDI', 'CDD', 'INTERIM', 'FREELANCE']
        if v.upper() not in valid_types:
            raise ValueError(f'Contract type must be one of {valid_types}')
        return v.upper()

class PropertyInfo(BaseModel):
    type: PropertyType
    address: Address
    surface_area: float = Field(..., gt=0)
    construction_year: Optional[int] = None
    description: str
    estimated_value: Optional[Decimal] = None
    
    @validator('construction_year')
    def validate_year(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v < 1800 or v > current_year:
                raise ValueError(f'Construction year must be between 1800 and {current_year}')
        return v

class LoanRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"LOAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    status: LoanRequestStatus = Field(default=LoanRequestStatus.DRAFT)
    
    # Personal Information
    client_name: str
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    birth_date: datetime
    nationality: str
    current_address: Address
    
    # Loan Details
    loan_amount: Decimal = Field(..., gt=0)
    loan_purpose: LoanPurpose
    loan_duration_years: int = Field(..., ge=5, le=30)
    
    # Financial Information
    employment_info: EmploymentInfo
    monthly_income: Decimal = Field(..., gt=0)
    monthly_expenses: Decimal = Field(..., ge=0)
    existing_loans: Optional[List[Dict[str, Decimal]]] = []
    
    # Property Information
    property_info: PropertyInfo
    
    # Tracking Information
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    
    @validator('monthly_expenses')
    def validate_expenses(cls, v, values):
        if 'monthly_income' in values and v >= values['monthly_income']:
            raise ValueError('Monthly expenses cannot exceed monthly income')
        return v
    
    @validator('loan_amount')
    def validate_loan_amount(cls, v):
        min_amount = Decimal('50000')
        max_amount = Decimal('2000000')
        if v < min_amount or v > max_amount:
            raise ValueError(f'Loan amount must be between {min_amount} and {max_amount} €')
        return v

class LoanRequestUpdate(BaseModel):
    status: LoanRequestStatus
    details: Optional[Dict] = None
    updated_at: datetime = Field(default_factory=datetime.now)

class LoanRequestError(BaseModel):
    request_id: str
    error_code: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict] = None

class Document(BaseModel):
    document_id: str
    request_id: str
    document_type: str
    file_name: str
    file_size: int
    mime_type: str
    upload_date: datetime = Field(default_factory=datetime.now)
    status: str = "PENDING_VALIDATION"
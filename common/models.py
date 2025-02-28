from pydantic import BaseModel, Field, EmailStr, validator, constr
from typing import Optional, Dict, List, Union
from datetime import datetime
from enum import Enum
from decimal import Decimal
import re

class BaseStatus(str, Enum):
    """Base status enum for all services"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class BaseError(BaseModel):
    """Base error model for all services"""
    error_code: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict] = None
    service: str
    correlation_id: Optional[str] = None

class Address(BaseModel):
    """Common address model"""
    street: str
    city: str
    postal_code: str = Field(..., regex=r'^\d{5}$')
    country: str = "France"
    
    @validator('postal_code')
    def validate_french_postal_code(cls, v):
        if not re.match(r'^\d{5}$', v):
            raise ValueError('Invalid French postal code')
        return v

class PersonalInfo(BaseModel):
    """Common personal information model"""
    first_name: str
    last_name: str
    email: EmailStr
    phone: constr(regex=r'^\+?[0-9]{10,15}$')
    birth_date: datetime
    nationality: str
    current_address: Address

class FinancialInfo(BaseModel):
    """Common financial information model"""
    monthly_income: Decimal = Field(..., gt=0)
    monthly_expenses: Decimal = Field(..., ge=0)
    existing_loans: List[Dict[str, Decimal]] = []
    employment_type: str = Field(..., regex='^(CDI|CDD|INTERIM|FREELANCE)$')
    employer_name: str
    employment_length_years: float = Field(..., ge=0)
    
    @validator('monthly_expenses')
    def validate_expenses(cls, v, values):
        if 'monthly_income' in values and v >= values['monthly_income']:
            raise ValueError('Monthly expenses cannot exceed monthly income')
        return v

class EventBase(BaseModel):
    """Base event model for message broker"""
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: str
    service: str
    data: Dict
    metadata: Optional[Dict] = None

class AuditLog(BaseModel):
    """Audit log entry model"""
    timestamp: datetime = Field(default_factory=datetime.now)
    service: str
    action: str
    user_id: Optional[str]
    request_id: str
    details: Dict
    status: str
    duration_ms: Optional[float]

class ServiceHealth(BaseModel):
    """Service health check model"""
    service: str
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Dict[str, Any] = Field(default_factory=dict)
    dependencies: Dict[str, bool] = Field(default_factory=dict)

class MetricData(BaseModel):
    """Metric data model for monitoring"""
    metric_name: str
    metric_type: str
    value: Union[int, float, str]
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class DocumentInfo(BaseModel):
    """Common document information model"""
    document_id: str = Field(default_factory=lambda: f"DOC_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    document_type: str
    file_name: str
    file_size: int
    mime_type: str
    upload_date: datetime = Field(default_factory=datetime.now)
    status: str = "PENDING"
    metadata: Optional[Dict] = None
    
    @validator('mime_type')
    def validate_mime_type(cls, v):
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if v not in allowed_types:
            raise ValueError(f'Unsupported file type. Allowed types: {allowed_types}')
        return v

class ValidationResult(BaseModel):
    """Common validation result model"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    details: Optional[Dict] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ProcessStep(BaseModel):
    """Process step tracking model"""
    step_name: str
    status: BaseStatus
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error: Optional[BaseError] = None
    metadata: Dict = Field(default_factory=dict)

class WorkflowState(BaseModel):
    """Workflow state tracking model"""
    workflow_id: str
    current_step: str
    steps_completed: List[ProcessStep]
    steps_remaining: List[str]
    status: BaseStatus
    start_time: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    metadata: Dict = Field(default_factory=dict)

class ServiceConfig(BaseModel):
    """Service configuration model"""
    service_name: str
    version: str
    environment: str
    debug_mode: bool = False
    log_level: str = "INFO"
    timeout_seconds: int = 30
    retry_count: int = 3
    dependencies: Dict[str, str]
    feature_flags: Dict[str, bool] = Field(default_factory=dict)

class ApiResponse(BaseModel):
    """Standard API response model"""
    success: bool
    message: str
    data: Optional[Dict] = None
    errors: List[BaseError] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
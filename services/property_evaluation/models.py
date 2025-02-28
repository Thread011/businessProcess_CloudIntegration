from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal

class PropertyType(str, Enum):
    APARTMENT = "APARTMENT"
    HOUSE = "HOUSE"
    COMMERCIAL = "COMMERCIAL"
    LAND = "LAND"

class PropertyCondition(str, Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    RENOVATION_NEEDED = "RENOVATION_NEEDED"

class LocationQuality(str, Enum):
    PREMIUM = "PREMIUM"
    GOOD = "GOOD"
    AVERAGE = "AVERAGE"
    BELOW_AVERAGE = "BELOW_AVERAGE"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

class Address(BaseModel):
    street: str
    city: str
    postal_code: str
    country: str = "France"
    
    @validator('postal_code')
    def validate_postal_code(cls, v):
        if not v.isdigit() or len(v) != 5:
            raise ValueError("Invalid French postal code")
        return v

class PropertyDetails(BaseModel):
    property_type: PropertyType
    surface_area: float = Field(..., gt=0)
    rooms: Optional[int] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0)
    construction_year: Optional[int] = None
    floor_number: Optional[int] = None
    total_floors: Optional[int] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    energy_rating: Optional[str] = None
    
    @validator('construction_year')
    def validate_year(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v < 1800 or v > current_year:
                raise ValueError(f'Construction year must be between 1800 and {current_year}')
        return v

class MarketAnalysis(BaseModel):
    average_price_per_m2: Decimal
    price_trend_6m: float  # Percentage
    price_trend_1y: float  # Percentage
    average_time_on_market: int  # Days
    comparable_properties: List[Dict[str, Any]]
    location_rating: LocationQuality

    model_config = {
        "arbitrary_types_allowed": True
    }

class PropertyEvaluation(BaseModel):
    evaluation_id: str = Field(default_factory=lambda: f"EVAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    request_id: str
    address: Address
    property_details: PropertyDetails
    market_analysis: MarketAnalysis
    estimated_value: Decimal
    confidence_score: float = Field(..., ge=0, le=1)
    condition_assessment: PropertyCondition
    risk_assessment: RiskLevel
    evaluation_date: datetime = Field(default_factory=datetime.now)
    evaluator: Optional[str] = None
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        return v

    model_config = {
        "arbitrary_types_allowed": True
    }

class EvaluationRequest(BaseModel):
    request_id: str
    address: Address
    property_details: PropertyDetails
    loan_amount: Decimal
    additional_info: Optional[Dict] = None

class EvaluationError(BaseModel):
    evaluation_id: str
    request_id: str
    error_code: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict] = None
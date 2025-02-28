from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    INTERNAL = "INTERNAL"

class NotificationPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"
    READ = "READ"

class NotificationTemplate(str, Enum):
    LOAN_REQUEST_RECEIVED = "LOAN_REQUEST_RECEIVED"
    DOCUMENTS_REQUIRED = "DOCUMENTS_REQUIRED"
    APPLICATION_INCOMPLETE = "APPLICATION_INCOMPLETE"
    APPLICATION_APPROVED = "APPLICATION_APPROVED"
    APPLICATION_REJECTED = "APPLICATION_REJECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    AGREEMENT_READY = "AGREEMENT_READY"

class Recipient(BaseModel):
    client_id: str
    name: str
    language: str = "fr"  # Default to French

class NotificationContent(BaseModel):
    subject: str
    body: str
    template_id: NotificationTemplate
    variables: Dict[str, str] = {}
    status: str

class NotificationRequest(BaseModel):
    request_id: str
    notification_type: NotificationType = NotificationType.INTERNAL  # Default to INTERNAL only
    priority: NotificationPriority = NotificationPriority.MEDIUM
    recipient: Recipient
    content: NotificationContent
    scheduled_time: Optional[datetime] = None
    metadata: Optional[Dict] = Field(default_factory=dict)

class NotificationResult(BaseModel):
    notification_id: str = Field(default_factory=lambda: f"NOTIF_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    request_id: str
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    channel_response: Optional[Dict] = None
    error: Optional[str] = None

class NotificationError(BaseModel):
    notification_id: str
    request_id: str
    error_code: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    retry_count: int = 0
    details: Optional[Dict] = None
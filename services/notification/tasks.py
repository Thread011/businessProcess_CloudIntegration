from common.celery_app import celery_app, TASK_LATENCY, TASK_FAILURE_COUNTER
from celery.utils.log import get_task_logger
from .models import (
    NotificationRequest, NotificationResult, NotificationError,
    NotificationStatus, NotificationType
)
from typing import Dict
from datetime import datetime
from functools import wraps
import time
from .websocket import NotificationManager

logger = get_task_logger(__name__)
notification_manager = NotificationManager()

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

@celery_app.task(name='notification.send_notification')
@monitor_task
def send_notification(notification_request: Dict) -> Dict:
    """Send a notification via Celery task"""
    try:
        request = NotificationRequest(**notification_request)
        
        # Create notification ID
        notification_id = f"NOTIF_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Log the notification
        logger.info(
            f"Sending notification {notification_id} to {request.recipient.client_id}: "
            f"{request.content.subject} - {request.content.body}"
        )
        
        # Create result
        result = {
            "notification_id": notification_id,
            "request_id": request.request_id,
            "status": NotificationStatus.SENT,
            "sent_at": datetime.now().isoformat(),
            "recipient": request.recipient.dict(),
            "content": request.content.dict()
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")
        raise NotificationError(
            notification_id=f"ERROR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            request_id=notification_request.get("request_id", "unknown"),
            error_code="NOTIFICATION_FAILED",
            error_message=str(e)
        )
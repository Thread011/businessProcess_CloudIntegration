from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .models import (
    DecisionRequest, DecisionResult, DecisionStatus, DecisionReason,
    DecisionError
)
from .tasks import evaluate_application
from common.messaging import MessageBroker
import os
import json
import logging
import redis
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

app = FastAPI(title="Loan Decision Service")
message_broker = MessageBroker()

def get_redis_client():
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = int(os.environ.get('REDIS_PORT', 6379))
    return redis.Redis(host=redis_host, port=redis_port, db=0)

@app.post("/decisions/", response_model=DecisionResult)
async def create_decision(request: DecisionRequest, background_tasks: BackgroundTasks):
    """Create a new decision request"""
    try:
        logger.info(f"Received decision request: {request.request_id}")
        
        # Validate request data
        if not request.criteria:
            raise ValueError("Missing decision criteria")
            
        # Start with PENDING status
        result = DecisionResult(
            request_id=request.request_id,
            status=DecisionStatus.PENDING,
            reasons=[],
            details={}
        )
        
        # Process decision asynchronously
        background_tasks.add_task(process_decision_async, request)
        
        # Store initial result in Redis for retrieval
        redis_client = get_redis_client()
        redis_client.set(f"decision:{request.request_id}", json.dumps(result.dict()))
        
        return result
        
    except Exception as e:
        error = DecisionError(
            request_id=request.request_id,
            error_code="DECISION_ERROR",
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=error.dict())

async def process_decision_async(request: DecisionRequest):
    """Process decision asynchronously"""
    try:
        # Start evaluation task
        task = evaluate_application.delay(request.dict())
        
        # Wait for result (with longer timeout)
        result = task.get(timeout=60)
        decision_result = DecisionResult(**result)
        
        # Store the result in Redis
        redis_client = get_redis_client()
        redis_client.set(f"decision:{request.request_id}", json.dumps(decision_result.dict()))
        
        # Publish decision event
        await publish_decision_event(decision_result)
        
    except Exception as e:
        logger.error(f"Async decision processing failed: {str(e)}")
        # We don't raise the exception here since this is running in the background

@app.get("/decisions/{request_id}")
async def get_decision(request_id: str):
    try:
        # Retrieve result from Redis
        redis_client = get_redis_client()
        result_json = redis_client.get(f"decision:{request_id}")
        
        if result_json:
            result_dict = json.loads(result_json)
            return result_dict
        else:
            return {"status": "PENDING", "request_id": request_id}
            
    except Exception as e:
        logger.error(f"Error retrieving decision: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Decision not found: {str(e)}")

async def publish_decision_event(decision: DecisionResult):
    """Publish decision event to message broker"""
    event_type = (
        "loan.decision.approved" if decision.status == DecisionStatus.APPROVED
        else "loan.decision.rejected" if decision.status == DecisionStatus.REJECTED
        else "loan.decision.review_needed"
    )
    
    # Create notification for the dashboard
    notification_data = {
        "request_id": decision.request_id,
        "notification_type": "INTERNAL",
        "priority": "HIGH",
        "recipient": {
            "client_id": decision.request_id,
            "name": "Client",
            "language": "fr"
        },
        "content": {
            "subject": f"Loan Decision: {decision.status.value}",
            "body": f"Your loan application has been {decision.status.value.lower()}",
            "template_id": "APPLICATION_APPROVED" if decision.status == DecisionStatus.APPROVED 
                      else "APPLICATION_REJECTED" if decision.status == DecisionStatus.REJECTED
                      else "REVIEW_REQUIRED",
            "variables": {
                "decision_status": decision.status.value,
                "interest_rate": f"{decision.proposed_rate:.2f}%" if decision.proposed_rate else "N/A",
                "decision_date": decision.decision_date.isoformat()
            },
            "status": "PENDING"
        }
    }
    
    # Send notification to the notification service
    try:
        import requests
        notification_service_url = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service:8000')
        response = requests.post(
            f"{notification_service_url}/notifications/",
            json=notification_data
        )
        logger.info(f"Notification sent: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Notification error: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")
    
    # Also publish to the message broker
    await message_broker.publish_event(
        event_type=event_type,
        routing_key=f"loan.decision.{decision.status.lower()}",
        data=decision.dict()
    )

@app.post("/decisions/{request_id}/manual-review")
async def manual_review_decision(
    request_id: str,
    review_result: dict,
    background_tasks: BackgroundTasks
):
    try:
        # Update decision with manual review result
        decision_result = DecisionResult(
            request_id=request_id,
            status=DecisionStatus(review_result["status"]),
            reasons=[review_result["reason"]],
            details=review_result.get("details", {}),
            reviewer=review_result["reviewer"]
        )
        
        # Store the result in Redis
        redis_client = get_redis_client()
        redis_client.set(f"decision:{request_id}", json.dumps(decision_result.dict()))
        
        # Publish manual review event
        background_tasks.add_task(
            publish_decision_event,
            decision_result
        )
        
        return decision_result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Manual review failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "decision-service"}

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import aio_pika
import json
from redis import Redis, RedisError
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Loan Request Service")

# Pydantic models
class LoanRequest(BaseModel):
    client_name: str
    address: str
    email: str
    phone: str
    loan_amount: float
    loan_duration_years: int
    property_description: str
    monthly_income: float
    monthly_expenses: float

class LoanRequestResponse(BaseModel):
    request_id: str
    status: str
    timestamp: datetime

# Initialize Redis
def get_redis_client():
    try:
        redis_client = Redis(host='redis', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        return redis_client
    except RedisError as e:
        logger.error(f"Redis connection error: {str(e)}")
        return None

redis_client = get_redis_client()

@app.post("/loan-requests/", response_model=Dict)
async def create_loan_request(request: dict):
    try:
        # Generate request ID
        request_id = f"LOAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Creating loan request with ID: {request_id}")
        
        # Store loan request in Redis
        loan_data = {
            "request_id": request_id,
            "status": "PENDING",
            "timestamp": datetime.now().isoformat(),
            **request
        }
        
        if not redis_client:
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable"
            )
            
        # Store in Redis with 24-hour expiry
        logger.info(f"Storing loan request in Redis: {request_id}")
        redis_client.setex(
            f"loan_request:{request_id}",
            86400,  # 24 hours
            json.dumps(loan_data)
        )
        
        # Prepare message for credit check - simplified structure
        credit_check_message = {
            "request_id": request_id,
            "monthly_income": float(request["monthly_income"]),
            "monthly_expenses": float(request["monthly_expenses"]),
            "loan_amount": float(request["loan_amount"]),
            "client_name": request["client_name"]
        }
        
        logger.info(f"Preparing to publish message: {credit_check_message}")
        
        # Publish to RabbitMQ
        connection = await aio_pika.connect_robust(
            host="rabbitmq",
            port=5672,
            login="guest",
            password="guest"
        )
        
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                    "loan_processing",
                    aio_pika.ExchangeType.TOPIC,
                    durable=True  # Add this line
                )
            
            message = aio_pika.Message(
                body=json.dumps({
                    "type": "LOAN_REQUEST_CREATED",
                    "data": {
                        "request_id": request_id,
                        "monthly_income": float(request["monthly_income"]),
                        "monthly_expenses": float(request["monthly_expenses"]),
                        "loan_amount": float(request["loan_amount"]),
                        "client_name": request["client_name"]
                    },
                    "timestamp": datetime.now().isoformat()
                }).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
)
            
            await exchange.publish(
                message,
                routing_key="loan.request.created"
            )
            logger.info(f"Message published successfully for request: {request_id}")
        
        return {
            "request_id": request_id,
            "status": "RECEIVED",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating loan request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/loan-requests/{request_id}")
async def get_loan_request(request_id: str):
    try:
        if not redis_client:
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable"
            )
            
        # Get loan request from Redis
        loan_data = redis_client.get(f"loan_request:{request_id}")
        
        if not loan_data:
            raise HTTPException(
                status_code=404,
                detail=f"Loan request {request_id} not found"
            )
            
        return json.loads(loan_data)
        
    except RedisError as e:
        logger.error(f"Redis error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"Error retrieving loan request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    if not redis_client:
        raise HTTPException(
            status_code=503,
            detail="Redis connection not available"
        )
    try:
        redis_client.ping()
        return {"status": "healthy"}
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Redis health check failed"
        )
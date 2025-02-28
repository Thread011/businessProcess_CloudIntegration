from fastapi import FastAPI, HTTPException, logger, Response
from .models import (
    EvaluationRequest, PropertyEvaluation, EvaluationError,
    PropertyType, PropertyCondition, LocationQuality
)
from .tasks import evaluate_property
from common.messaging import MessageBroker
import aio_pika
import json
from datetime import datetime
import asyncio
import random
from decimal import Decimal

app = FastAPI(title="Property Evaluation Service")
message_broker = MessageBroker()

@app.post("/evaluations/")
async def create_evaluation(request: EvaluationRequest):
    try:
        # Evaluate property directly (no longer using Celery)
        # Pass None as the first argument to match the function signature
        result = evaluate_property(None, request.dict())
        
        # Publish evaluation result to RabbitMQ
        await publish_evaluation_result(result)
        
        return PropertyEvaluation(**result)
            
    except Exception as e:
        logger.error(f"Property evaluation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/evaluations/{request_id}")
async def get_evaluation(request_id: str):
    """
    Simple mock endpoint that returns a fixed property evaluation
    """
    try:
        # Return a fixed property evaluation
        return {
            "request_id": request_id,
            "estimated_value": 350000.0,
            "risk_assessment": "LOW",
            "ltv_ratio": 0.65,
            "confidence_score": 0.85,
            "condition_assessment": "GOOD",
            "evaluation_date": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to retrieve property evaluation: {str(e)}")
        raise HTTPException(status_code=404, detail="Evaluation not found")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "property-evaluation-service"}

async def publish_evaluation_result(evaluation_result: dict):
    """Publishes evaluation result to RabbitMQ"""
    try:
        connection = await aio_pika.connect_robust(
            host="rabbitmq",
            port=5672,
            login="guest",
            password="guest"
        )
        
        async with connection:
            channel = await connection.channel()
            
            # Declare exchange
            exchange = await channel.declare_exchange(
                "loan_processing",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Prepare message
            message = {
                "type": "PROPERTY_EVALUATION_COMPLETED",
                "data": evaluation_result,
                "timestamp": datetime.now().isoformat()
            }
            
            # Publish message
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key="property.evaluation.completed"
            )
            logger.info(f"Published evaluation result: {evaluation_result['request_id']}")
            
    except aio_pika.exceptions.AMQPError as e:
        logger.error(f"RabbitMQ error while publishing evaluation result: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Failed to publish evaluation result"
        )
    except Exception as e:
        logger.error(f"Unexpected error while publishing evaluation result: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process evaluation result: {str(e)}"
        )
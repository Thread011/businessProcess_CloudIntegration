from fastapi import FastAPI, BackgroundTasks, HTTPException
from redis import Redis, RedisError
import json
from datetime import datetime
import logging
import aio_pika
import asyncio
import random
from typing import Dict, Any

logger = logging.getLogger(__name__)

app = FastAPI(title="Credit Check Service")

# Initialize Redis with retry logic
def get_redis_client():
    try:
        redis_client = Redis(host='redis', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        return redis_client
    except RedisError as e:
        logger.error(f"Redis connection error: {str(e)}")
        return None

redis_client = get_redis_client()

def calculate_credit_score(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate a realistic credit score based on multiple financial factors.
    
    The score is calculated using:
    - Income to loan ratio
    - Debt-to-income ratio
    - Loan duration (longer terms are slightly riskier)
    - Previous payment history (simulated)
    
    Returns a dictionary with the credit score and detailed factors.
    """
    try:
        # Extract required data
        monthly_income = float(client_data.get('monthly_income', 0))
        monthly_expenses = float(client_data.get('monthly_expenses', 0))
        loan_amount = float(client_data.get('loan_amount', 0))
        loan_duration_years = int(client_data.get('loan_duration_years', 20))
        
        # Calculate base metrics
        dti_ratio = monthly_expenses / monthly_income if monthly_income > 0 else 1.0
        income_to_loan_ratio = (monthly_income * 12 * loan_duration_years) / loan_amount if loan_amount > 0 else 0
        
        # Base score starts at 500
        base_score = 500
        
        # Income to loan ratio factor (0-200 points)
        # Higher ratio is better - means income is high relative to loan
        if income_to_loan_ratio >= 2.0:
            income_factor = 200  # Excellent
        elif income_to_loan_ratio >= 1.5:
            income_factor = 150  # Very good
        elif income_to_loan_ratio >= 1.0:
            income_factor = 100  # Good
        elif income_to_loan_ratio >= 0.75:
            income_factor = 50   # Fair
        else:
            income_factor = 0    # Poor
            
        # DTI ratio factor (0-200 points)
        # Lower ratio is better
        if dti_ratio <= 0.25:
            dti_factor = 200     # Excellent
        elif dti_ratio <= 0.33:
            dti_factor = 150     # Very good
        elif dti_ratio <= 0.43:
            dti_factor = 100     # Good
        elif dti_ratio <= 0.50:
            dti_factor = 50      # Fair
        else:
            dti_factor = 0       # Poor
            
        # Loan duration factor (0-50 points)
        # Shorter terms are slightly better
        if loan_duration_years <= 10:
            duration_factor = 50  # Excellent
        elif loan_duration_years <= 15:
            duration_factor = 40  # Very good
        elif loan_duration_years <= 20:
            duration_factor = 30  # Good
        elif loan_duration_years <= 25:
            duration_factor = 20  # Fair
        else:
            duration_factor = 10  # Poor
            
        # Payment history factor (0-150 points)
        # In a real system, this would come from credit bureau data
        # For simulation, we'll generate a semi-random score based on other factors
        # Higher income to loan ratio and lower DTI tend to correlate with better payment history
        payment_history_base = ((income_factor / 200) * 0.7 + (dti_factor / 200) * 0.3) * 150
        # Add some randomness to simulate real-world variability
        payment_history_factor = max(0, min(150, payment_history_base + random.randint(-20, 20)))
        
        # Calculate final score (range 500-900)
        credit_score = int(base_score + income_factor + dti_factor + duration_factor + payment_history_factor)
        
        # Cap the score at 900
        credit_score = min(900, credit_score)
        
        return {
            "credit_score": credit_score,
            "dti_ratio": dti_ratio,
            "income_to_loan_ratio": income_to_loan_ratio,
            "factors": {
                "income_factor": income_factor,
                "dti_factor": dti_factor,
                "duration_factor": duration_factor,
                "payment_history_factor": payment_history_factor
            }
        }
    except Exception as e:
        logger.error(f"Error calculating credit score: {str(e)}")
        # Return a default score if calculation fails
        return {
            "credit_score": 550,  # Below threshold
            "dti_ratio": 1.0,
            "income_to_loan_ratio": 0,
            "factors": {
                "income_factor": 0,
                "dti_factor": 0,
                "duration_factor": 0,
                "payment_history_factor": 0
            },
            "error": str(e)
        }

async def process_credit_check(message_data: dict):
    try:
        logger.info(f"Starting credit check process with data: {message_data}")
        
        # Extract request_id directly from message data
        request_id = message_data.get('request_id')
        if not request_id:
            raise ValueError("No request ID in message data")
        
        logger.info(f"Processing credit check for request ID: {request_id}")
        
        if not redis_client:
            raise Exception("Redis client is not available")
        
        # Calculate credit score with realistic algorithm
        credit_assessment = calculate_credit_score(message_data)
        credit_score = credit_assessment["credit_score"]
        dti_ratio = credit_assessment["dti_ratio"]
        
        # Determine eligibility based on credit score and DTI ratio
        is_eligible = credit_score >= 650 and dti_ratio <= 0.43
        
        result = {
            "request_id": request_id,
            "credit_score": credit_score,
            "dti_ratio": dti_ratio,
            "is_eligible": is_eligible,
            "status": "COMPLETED",
            "assessment_details": credit_assessment["factors"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Store result in Redis
        logger.info(f"Storing result for request ID: {request_id}")
        redis_client.setex(
            f"credit_check:{request_id}", 
            3600,  # expire in 1 hour
            json.dumps(result)
        )
        logger.info(f"Credit check completed for request ID: {request_id}")
        
        # Publish the result to RabbitMQ
        await publish_credit_check_result(result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in credit check process: {str(e)}")
        if redis_client and 'request_id' in message_data:
            error_result = {
                "request_id": message_data['request_id'],
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            try:
                redis_client.setex(
                    f"credit_check:{message_data['request_id']}", 
                    3600,
                    json.dumps(error_result)
                )
            except RedisError as re:
                logger.error(f"Failed to store error result in Redis: {str(re)}")
        raise

async def publish_credit_check_result(result: dict):
    """Publish credit check result to RabbitMQ."""
    try:
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
                durable=True
            )
            
            message = aio_pika.Message(
                body=json.dumps({
                    "type": "CREDIT_CHECK_COMPLETED",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            
            await exchange.publish(
                message,
                routing_key="credit.check.completed"
            )
            
            logger.info(f"Published credit check result for request {result['request_id']}")
    except Exception as e:
        logger.error(f"Failed to publish credit check result: {str(e)}")

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            message_body = message.body.decode()
            logger.info(f"Received raw message: {message_body}")
            
            message_data = json.loads(message_body)
            logger.info(f"Parsed message data: {message_data}")
            
            # Add this debugging
            if isinstance(message_data, dict) and 'data' in message_data:
                message_data = message_data['data']
            
            if not message_data.get('request_id'):
                logger.error(f"No request ID found in message: {message_data}")
                raise ValueError("No request ID in message data")
                
            await process_credit_check(message_data)
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

async def process_loan_requests():
    while True:
        try:
            logger.info("Connecting to RabbitMQ...")
            connection = await aio_pika.connect_robust(
                host="rabbitmq",
                port=5672,
                login="guest",
                password="guest"
            )

            async with connection:
                channel = await connection.channel()
                logger.info("Connected to RabbitMQ successfully")
                
                exchange = await channel.declare_exchange(
                    "loan_processing",
                    aio_pika.ExchangeType.TOPIC,
                    durable=True
                )
                logger.info("Exchange declared")

                queue = await channel.declare_queue(
                    "credit_check_queue", 
                    durable=True
                )
                logger.info("Queue declared")
                
                await queue.bind(
                    exchange=exchange,
                    routing_key="loan.request.created"
                )
                logger.info("Queue bound to exchange")

                await queue.consume(process_message)
                logger.info("Started consuming messages")
                
                try:
                    await asyncio.Future()  # run forever
                except Exception as e:
                    logger.error(f"Consumer error: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            await asyncio.sleep(5)
            continue

@app.get("/credit-check/{request_id}")
async def get_credit_check_status(request_id: str):
    try:
        logger.info(f"Checking credit status for request ID: {request_id}")
        
        if not redis_client:
            logger.error("Redis client is not available")
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable"
            )
        
        # Try to get result from Redis
        result = redis_client.get(f"credit_check:{request_id}")
        
        if result:
            logger.info(f"Found result for request ID: {request_id}")
            return json.loads(result)
        
        logger.warning(f"No result found for request ID: {request_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Credit check not found for request ID: {request_id}"
        )
    except RedisError as e:
        logger.error(f"Redis error for request {request_id}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_loan_requests())
    logger.info("Credit check service started")

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
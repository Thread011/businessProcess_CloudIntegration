from fastapi import FastAPI, BackgroundTasks, HTTPException
from redis import Redis, RedisError
import json
from datetime import datetime
import logging
import aio_pika
import asyncio

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
        
        # Process credit check with data from message
        credit_score = 700  # Simulated score
        monthly_income = float(message_data['monthly_income'])
        monthly_expenses = float(message_data['monthly_expenses'])
        dti_ratio = monthly_expenses / monthly_income
        
        result = {
            "request_id": request_id,
            "credit_score": credit_score,
            "dti_ratio": dti_ratio,
            "is_eligible": credit_score >= 650 and dti_ratio <= 0.43,
            "status": "COMPLETED",
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
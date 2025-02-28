import aio_pika
import asyncio
import json
import logging
from datetime import datetime
import os
from .tasks import evaluate_property

logger = logging.getLogger(__name__)

async def process_message(message: aio_pika.IncomingMessage):
    """Process incoming messages from RabbitMQ"""
    async with message.process():
        try:
            # Parse message body
            message_body = message.body.decode()
            message_data = json.loads(message_body)
            
            logger.info(f"Received message: {message.message_id}")
            logger.debug(f"Message data: {message_data}")
            
            # Extract loan request data
            if 'data' in message_data:
                request_data = message_data['data']
                
                # Process credit check result
                if message_data.get('type') == 'CREDIT_CHECK_COMPLETED':
                    await process_credit_check_result(request_data)
                # Process loan request
                elif message_data.get('type') == 'LOAN_REQUEST_CREATED':
                    await process_loan_request(request_data)
                else:
                    logger.warning(f"Unknown message type: {message_data.get('type')}")
            else:
                logger.warning("Message missing 'data' field")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

async def process_credit_check_result(credit_check_data: dict):
    """Process credit check result and perform property evaluation"""
    try:
        logger.info(f"Processing credit check result for request ID: {credit_check_data.get('request_id')}")
        
        # Only proceed if credit check was successful
        if credit_check_data.get('is_eligible', False):
            # Extract property details from the credit check data
            # This assumes the credit check data contains property information
            # In a real system, you might need to fetch this from a database
            property_data = {
                'request_id': credit_check_data.get('request_id'),
                'property_address': credit_check_data.get('property_address', {}),
                'property_details': credit_check_data.get('property_details', {}),
                'loan_amount': credit_check_data.get('loan_amount', 0)
            }
            
            # Evaluate the property
            result = evaluate_property(None, property_data)
            
            # Publish the result
            from .api import publish_evaluation_result
            await publish_evaluation_result(result)
            
            logger.info(f"Property evaluation completed for request ID: {credit_check_data.get('request_id')}")
        else:
            logger.info(f"Credit check failed, skipping property evaluation for request ID: {credit_check_data.get('request_id')}")
            
    except Exception as e:
        logger.error(f"Error processing credit check result: {str(e)}")

async def process_loan_request(loan_request_data: dict):
    """Process loan request and extract property information for evaluation"""
    try:
        request_id = loan_request_data.get('request_id')
        logger.info(f"Processing loan request for request ID: {request_id}")
        
        # Extract property details from the loan request
        property_data = {
            'request_id': request_id,
            'property_address': loan_request_data.get('property_address', {}),
            'property_details': loan_request_data.get('property_details', {}),
            'loan_amount': loan_request_data.get('loan_amount', 0)
        }
        
        # Evaluate the property
        result = evaluate_property(None, property_data)
        
        # Publish the result
        from .api import publish_evaluation_result
        await publish_evaluation_result(result)
        
        logger.info(f"Property evaluation completed for request ID: {request_id}")
        
    except Exception as e:
        logger.error(f"Error processing loan request: {str(e)}")

async def start_consumer():
    """Start the RabbitMQ consumer"""
    rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
    rabbitmq_port = int(os.environ.get('RABBITMQ_PORT', 5672))
    rabbitmq_user = os.environ.get('RABBITMQ_USER', 'guest')
    rabbitmq_password = os.environ.get('RABBITMQ_PASSWORD', 'guest')
    rabbitmq_vhost = os.environ.get('RABBITMQ_VHOST', '/')
    
    connection = None
    
    while True:
        try:
            # Connect to RabbitMQ
            connection = await aio_pika.connect_robust(
                host=rabbitmq_host,
                port=rabbitmq_port,
                login=rabbitmq_user,
                password=rabbitmq_password,
                virtualhost=rabbitmq_vhost
            )
            
            # Create channel
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            
            # Declare exchange
            exchange = await channel.declare_exchange(
                "loan_processing",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            logger.info("Exchange declared")
            
            # Declare queues
            property_eval_queue = await channel.declare_queue(
                "property_evaluation_queue", 
                durable=True
            )
            logger.info("Property evaluation queue declared")
            
            # Bind queues to exchange with appropriate routing keys
            await property_eval_queue.bind(
                exchange=exchange,
                routing_key="loan.request.created"
            )
            await property_eval_queue.bind(
                exchange=exchange,
                routing_key="credit.check.completed"
            )
            logger.info("Queues bound to exchange")
            
            # Start consuming messages
            await property_eval_queue.consume(process_message)
            logger.info("Started consuming messages")
            
            # Keep the consumer running
            try:
                await asyncio.Future()  # Run forever
            except Exception as e:
                logger.error(f"Consumer error: {str(e)}")
                if connection and not connection.is_closed:
                    await connection.close()
                    connection = None
                continue
                
        except aio_pika.exceptions.AMQPError as e:
            logger.error(f"AMQP error: {str(e)}")
            if connection and not connection.is_closed:
                await connection.close()
                connection = None
            await asyncio.sleep(5)  # Wait before reconnecting
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            if connection and not connection.is_closed:
                await connection.close()
                connection = None
            await asyncio.sleep(5)  # Wait before reconnecting

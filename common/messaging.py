import aio_pika
from typing import Dict, Any, Callable, Optional
import json
from datetime import datetime
import logging
from .config import RABBITMQ_CONFIG

logger = logging.getLogger(__name__)

class MessageBroker:
    def __init__(self, config: Dict = None):
        self.config = config or RABBITMQ_CONFIG
        self._connection: Optional[aio_pika.Connection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._connect_url = (
            f"amqp://{self.config['username']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}{self.config['vhost']}"
        )

    async def connect(self) -> None:
        """Establishes connection to RabbitMQ"""
        if not self._connection or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._connect_url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=1)

    async def close(self) -> None:
        """Closes the RabbitMQ connection"""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            self._channel = None

    async def publish_event(
        self,
        event_type: str,
        routing_key: str,
        data: Dict[str, Any]
    ) -> None:
        """Publishes an event to RabbitMQ"""
        try:
            if not self._connection or self._connection.is_closed:
                await self.connect()

            message = {
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }

            await self._channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    content_type="application/json"
                ),
                routing_key=routing_key
            )

        except Exception as e:
            raise Exception(f"Failed to publish message: {str(e)}")

    async def subscribe(
        self,
        queue_name: str,
        callback,
        routing_key: str = None
    ) -> None:
        """Subscribes to a queue"""
        try:
            if not self._connection or self._connection.is_closed:
                await self.connect()

            # Declare queue
            queue = await self._channel.declare_queue(
                queue_name,
                durable=True
            )

            if routing_key:
                await queue.bind(
                    exchange='amq.topic',
                    routing_key=routing_key
                )

            await queue.consume(callback)

        except Exception as e:
            raise Exception(f"Failed to subscribe to queue: {str(e)}")
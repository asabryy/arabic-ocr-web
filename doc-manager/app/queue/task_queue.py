import json
import pika
from app.core.config import settings

def publish_task(message: dict):
    connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))
    channel = connection.channel()

    # Ensure queue exists
    channel.queue_declare(queue=settings.RABBITMQ_QUEUE, durable=True)

    channel.basic_publish(
        exchange="",
        routing_key=settings.RABBITMQ_QUEUE,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2  # make message persistent
        )
    )

    connection.close()
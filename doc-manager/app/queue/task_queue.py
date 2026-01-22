import json
import pika
from app.core.config import settings

def publish_task(message: dict):
    rabbitmq_uri = settings.rabbitmq_uri or settings.rabbitmq_url
    if rabbitmq_uri:
        parameters = pika.URLParameters(rabbitmq_uri)
    else:
        parameters = pika.ConnectionParameters(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_port,
            credentials=pika.PlainCredentials(
                settings.rabbitmq_user,
                settings.rabbitmq_pass,
            ),
        )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    # Ensure queue exists
    channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)

    channel.basic_publish(
        exchange="",
        routing_key=settings.rabbitmq_queue,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2  # make message persistent
        )
    )

    connection.close()

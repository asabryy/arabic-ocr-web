import pika
import json
from app.core.config import settings

def publish_task(task: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=settings.rabbitmq_host)
    )
    channel = connection.channel()

    channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=settings.rabbitmq_queue,
        body=json.dumps(task),
        properties=pika.BasicProperties(delivery_mode=2),  # make message persistent
    )

    connection.close()

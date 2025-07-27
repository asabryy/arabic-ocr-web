import pika
import json
from app.core.config import settings

def publish_task(task: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
    )
    channel = connection.channel()

    channel.queue_declare(queue='doc_tasks', durable=True)
    channel.basic_publish(
        exchange='',
        routing_key='doc_tasks',
        body=json.dumps(task),
        properties=pika.BasicProperties(delivery_mode=2),  # make message persistent
    )

    connection.close()

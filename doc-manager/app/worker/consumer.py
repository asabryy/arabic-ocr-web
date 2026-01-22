# app/worker/consumer.py
import pika
import json
import logging
from app.core.config import settings

logger = logging.getLogger("doc-worker")
logging.basicConfig(level=logging.INFO)

def process_task(task):
    file_id = task.get("file_id")
    mode = task.get("mode")
    logger.info(f"Processing file: {file_id}, mode: {mode}")

    # TODO: Add actual processing logic here
    logger.info(f"Done processing {file_id} with mode {mode}")

def consume():
    # Added credentials and port
    credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_pass)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_port,
            credentials=credentials
        )
    )
    channel = connection.channel()

    # Use config-based queue name
    channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)
    logger.info(f"Waiting for messages in '{settings.rabbitmq_queue}' queue. To exit press CTRL+C")

    def callback(ch, method, properties, body):
        try:
            task = json.loads(body)
            process_task(task)
        except Exception as e:
            logger.error(f"Failed to process message: {body}, error: {e}")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=settings.rabbitmq_queue, on_message_callback=callback)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
        channel.stop_consuming()
        connection.close()

if __name__ == "__main__":
    consume()

import json

import pika

from app.core.config import settings

# A message that kills the worker mid-task (OOM on a large scan) is never acked, so
# RabbitMQ redelivers it forever — re-billing Gemini for every page it manages before
# dying, and with prefetch=1 blocking every other user's conversion. A quorum queue
# with a delivery limit drops such a message into the DLQ instead of looping.
QUEUE_ARGS = {
    "x-queue-type": "quorum",
    "x-delivery-limit": 3,
    "x-dead-letter-exchange": "",
    "x-dead-letter-routing-key": "",
}


def declare_task_queue(channel, queue: str) -> None:
    """Declare the work queue and its dead-letter queue.

    Falls back to a plain durable declare when the queue already exists with
    different arguments — RabbitMQ refuses to redeclare with changed arguments, and
    an existing deployment must not crash-loop on startup because of it. The DLQ
    name is derived so it is obvious where a stuck document went.
    """
    dlq = f"{queue}.dead"
    args = dict(QUEUE_ARGS)
    args["x-dead-letter-routing-key"] = dlq
    try:
        channel.queue_declare(queue=dlq, durable=True)
        channel.queue_declare(queue=queue, durable=True, arguments=args)
    except Exception:  # noqa: BLE001 — pre-existing queue with other arguments
        # The channel is closed by the failed declare; the caller reopens it.
        raise


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

    # Ensure the queue and its dead-letter queue exist.
    try:
        declare_task_queue(channel, settings.rabbitmq_queue)
    except Exception:  # noqa: BLE001
        # An existing classic queue cannot be redeclared with new arguments. Keep
        # publishing to it rather than failing the request; migrating the queue is
        # a deliberate operation, documented in the deployment notes.
        channel = connection.channel()
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

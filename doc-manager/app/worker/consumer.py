import io
import json
import logging
import time

import pika
import requests

from app.core.config import settings
from app.dependencies.storage import get_storage

logger = logging.getLogger("doc-worker")
logging.basicConfig(level=logging.INFO)

# OCR_BACKEND: "gemini" (prod — hosted Google Gemini vision, in-process) or
# "http" (local dev — POSTs the PDF to a self-hosted OCR server at OCR_HTTP_URL).
OCR_BACKEND  = settings.OCR_BACKEND
OCR_HTTP_URL = settings.OCR_HTTP_URL

# Retry config for RabbitMQ connection
_RETRY_DELAYS = [5, 10, 20, 40, 60]  # seconds between attempts


def _call_gemini(pdf_bytes: bytes, max_pages: int | None = None) -> bytes:
    from app.ocr.pipeline import process_pdf
    logger.info("Running Gemini OCR pipeline (%s, max_pages=%s)...", settings.GEMINI_MODEL, max_pages)
    docx_bytes = process_pdf(pdf_bytes, max_pages=max_pages)
    logger.info("Gemini OCR complete, produced %d bytes of DOCX", len(docx_bytes))
    return docx_bytes


def _call_http(pdf_bytes: bytes, max_pages: int | None = None) -> bytes:
    if max_pages:
        logger.warning("max_pages=%s is not supported by the http OCR backend; ignoring", max_pages)
    url = f"{OCR_HTTP_URL.rstrip('/')}/process"
    logger.info("Calling HTTP OCR pipeline at %s ...", url)
    resp = requests.post(
        url,
        files={"file": ("upload.pdf", pdf_bytes, "application/pdf")},
        timeout=600,
    )
    resp.raise_for_status()
    logger.info("HTTP OCR complete, received %d bytes of DOCX", len(resp.content))
    return resp.content


def _refund_pages(user_id: str, pages: int | None) -> None:
    """Best-effort: give a failed conversion's reserved pages back to the user's daily quota."""
    if not pages or user_id.startswith("trial/") or not settings.DATABASE_URL:
        return
    try:
        from app.db.session import get_engine
        from app.services import quota

        quota.release(get_engine(), int(user_id), pages)
        logger.info("Refunded %d pages to user %s", pages, user_id)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to refund %s pages to user %s: %s", pages, user_id, e)


def process_task(task: dict) -> None:
    file_id = task.get("file_id")
    user_id = task.get("user_id")
    mode = task.get("mode", "ocr")
    max_pages = task.get("max_pages")  # set for anonymous trials (first page only)
    pages = task.get("pages")          # reserved page count, for refund on failure

    if not file_id or not user_id:
        logger.error("Task missing file_id or user_id: %s", task)
        return

    storage = get_storage()
    storage.set_status(user_id, file_id, "processing")
    logger.info(
        "Processing file=%s user=%s mode=%s backend=%s max_pages=%s",
        file_id, user_id, mode, OCR_BACKEND, max_pages,
    )

    try:
        # ── Fetch PDF from storage (R2 presigned URL, or a local path in dev) ──
        pdf_url = storage.get_path(user_id, file_id)
        logger.info("Fetching PDF from storage...")
        if pdf_url.startswith("http"):
            resp = requests.get(pdf_url, timeout=120)
            resp.raise_for_status()
            pdf_bytes = resp.content
        else:
            with open(pdf_url, "rb") as f:
                pdf_bytes = f.read()
        logger.info("PDF fetched (%d bytes)", len(pdf_bytes))

        # ── Call OCR backend ────────────────────────────────────────────────
        if OCR_BACKEND == "http":
            docx_bytes = _call_http(pdf_bytes, max_pages)
        else:
            docx_bytes = _call_gemini(pdf_bytes, max_pages)

        # ── Save DOCX back to storage ───────────────────────────────────────
        stem = file_id.rsplit(".", 1)[0]
        docx_filename = f"{stem}.docx"
        storage.save_file(user_id, docx_filename, io.BytesIO(docx_bytes))
        logger.info("Saved DOCX as %s", docx_filename)

        storage.set_status(user_id, file_id, "done")
        logger.info("file=%s marked as done", file_id)

    except Exception as e:
        logger.error("Failed to process file=%s: %s", file_id, e, exc_info=True)
        storage.set_status(user_id, file_id, "failed")
        _refund_pages(user_id, pages)


def _connect() -> pika.BlockingConnection:
    """Connect to RabbitMQ with exponential backoff. Never returns until connected."""
    credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_pass)
    params = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=300,
    )
    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        try:
            connection = pika.BlockingConnection(params)
            if attempt > 1:
                logger.info("Connected to RabbitMQ after %d attempt(s).", attempt)
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(
                "RabbitMQ not ready (attempt %d/%d): %s — retrying in %ds",
                attempt, len(_RETRY_DELAYS), e, delay,
            )
            time.sleep(delay)
    # Final attempt — let it raise so k8s restarts with its own backoff
    return pika.BlockingConnection(params)


def consume() -> None:
    while True:
        connection = _connect()
        try:
            channel = connection.channel()
            channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)
            channel.basic_qos(prefetch_count=1)
            logger.info("Waiting for messages in '%s'. CTRL+C to exit.", settings.rabbitmq_queue)

            def callback(ch, method, properties, body):
                try:
                    task = json.loads(body)
                    process_task(task)
                except Exception as e:
                    logger.error("Unhandled error processing message: %s", e)
                finally:
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_consume(queue=settings.rabbitmq_queue, on_message_callback=callback)

            try:
                channel.start_consuming()
            except KeyboardInterrupt:
                logger.info("Shutting down consumer.")
                channel.stop_consuming()
                connection.close()
                return

        except (pika.exceptions.AMQPConnectionError, pika.exceptions.StreamLostError) as e:
            logger.warning("RabbitMQ connection lost: %s — reconnecting...", e)
            try:
                connection.close()
            except Exception:
                pass
            time.sleep(5)


if __name__ == "__main__":
    consume()

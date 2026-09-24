import html
import io
import json
import logging
import re
import threading
import time
import zipfile

import pika
import requests

from app import metrics
from app.core.config import settings
from app.dependencies.storage import get_storage
from app.queue.task_queue import declare_task_queue

logger = logging.getLogger("doc-worker")
logging.basicConfig(level=logging.INFO)

# OCR_BACKEND: "gemini" (prod — hosted Google Gemini vision, in-process) or
# "http" (local dev — POSTs the PDF to a self-hosted OCR server at OCR_HTTP_URL).
OCR_BACKEND  = settings.OCR_BACKEND
OCR_HTTP_URL = settings.OCR_HTTP_URL

# Retry config for RabbitMQ connection
_RETRY_DELAYS = [5, 10, 20, 40, 60]  # seconds between attempts

# Liveness marker. The metrics port is opened by a separate thread and stays open
# even if the consumer dies, so a TCP probe on it reports healthy through a total
# OCR outage. This file is touched from the consuming connection itself, so it
# goes stale exactly when consumption stops.
HEARTBEAT_PATH = "/tmp/worker-alive"
_HEARTBEAT_INTERVAL_S = 30


def touch_heartbeat() -> None:
    try:
        with open(HEARTBEAT_PATH, "w") as fh:
            fh.write(str(time.time()))
    except OSError as e:  # noqa: BLE001 — never let the probe marker kill the worker
        logger.warning("Could not write heartbeat file: %s", e)


def _call_gemini(pdf_bytes: bytes, max_pages: int | None = None, mode: str = "ocr") -> bytes:
    from app.ocr.pipeline import process_pdf
    logger.info("Running Gemini OCR pipeline (%s, max_pages=%s)...", settings.GEMINI_MODEL, max_pages)
    docx_bytes = process_pdf(pdf_bytes, max_pages=max_pages, mode=mode)
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


class EmptyOcrResult(Exception):
    """The pipeline finished, but produced a document with nothing readable in it.

    Raised, not returned, so the blank case lands on the same recovery path as a
    crash (status failed + quota refund) while still being counted separately.
    """

    def __init__(self, visible_chars: int, docx_bytes: int):
        super().__init__(f"{visible_chars} visible character(s) in {docx_bytes} bytes of DOCX")
        self.visible_chars = visible_chars
        self.docx_bytes = docx_bytes


# Text nodes in an OOXML document, and the separator the DOCX builder writes between
# pages ("-- Page 2 --"). The separator is chrome, not content: three image-only pages
# used to yield a file whose entire text was "-- Page 2 ---- Page 3 --". The pattern is
# deliberately loose (any dash/underscore/hash padding, "Page" or "صفحة") so a cosmetic
# change to that separator cannot quietly turn it back into "content".
_W_T_RE = re.compile(rb"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.DOTALL)
_PAGE_MARKER_RE = re.compile(
    r"^[\s\-–—_*=#.]*(?:page|صفحة)\s*\d+\s*[\s\-–—_*=#.]*$", re.IGNORECASE
)


def _docx_visible_chars(docx_bytes: bytes) -> int | None:
    """Count the non-whitespace characters a reader would actually see in a DOCX.

    Reads ``word/document.xml`` out of the zip rather than asking the OCR pipeline how
    much text it found: the file the user downloads is the only thing that matters, and
    this stays correct no matter how ``process_pdf`` is restructured internally — its
    public contract is "PDF bytes in, DOCX bytes out" and that is all this relies on.

    Returns ``None`` when the bytes are not a readable DOCX. Unreadable output is a
    different bug, and guessing "empty" there would fail conversions that are fine.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
            xml = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError, OSError, ValueError):
        return None

    total = 0
    for raw in _W_T_RE.findall(xml):
        text = html.unescape(raw.decode("utf-8", "replace")).strip()
        if not text or _PAGE_MARKER_RE.match(text):
            continue
        total += len("".join(text.split()))
    return total


def _notify_conversion_finished(
    user_id: str,
    file_id: str,
    outcome: str,
    elapsed_s: float,
    *,
    pages: int | None = None,
    reason: str | None = None,
) -> None:
    """Best-effort "your conversion finished" email, via auth-service.

    Cross-service shape: the worker POSTs a *user id* and an outcome to an internal
    auth-service endpoint, which owns the users table and the mail provider. Chosen
    over calling Resend from here because (a) doc-manager has no email column in its
    partial mirror of ``users`` and no mail credentials, and duplicating both is how
    two senders drift, and (b) an endpoint that takes a user id — never an address —
    cannot be turned into an open relay even if its shared key leaks.

    Every failure mode is swallowed. A conversion that succeeded stays succeeded; the
    worst a broken notifier can do is burn NOTIFY_TIMEOUT_S and bump a counter.
    """
    try:
        uid = str(user_id)
        if uid.startswith("trial/") or not uid.isdigit():
            # Anonymous trial: no account, no address, nothing to send to.
            metrics.CONVERSION_NOTIFICATIONS.labels(outcome="skipped").inc()
            return
        if not settings.NOTIFY_URL or not settings.NOTIFY_API_KEY:
            metrics.CONVERSION_NOTIFICATIONS.labels(outcome="skipped").inc()
            return
        if elapsed_s < settings.NOTIFY_MIN_SECONDS:
            # Short job: the Convert page is almost certainly still open and has
            # already shown the result. Mailing here is what turns a five-document
            # session into five emails.
            metrics.CONVERSION_NOTIFICATIONS.labels(outcome="skipped").inc()
            logger.info(
                "No notification for file=%s user=%s: %.0fs is under the %.0fs threshold",
                file_id, uid, elapsed_s, settings.NOTIFY_MIN_SECONDS,
            )
            return

        resp = requests.post(
            settings.NOTIFY_URL,
            json={
                "user_id": int(uid),
                "filename": file_id,
                "outcome": outcome,
                "pages": pages,
                "duration_seconds": round(elapsed_s, 1),
                "reason": reason,
            },
            headers={"X-Internal-Key": settings.NOTIFY_API_KEY},
            timeout=settings.NOTIFY_TIMEOUT_S,
        )
        resp.raise_for_status()
        metrics.CONVERSION_NOTIFICATIONS.labels(outcome="sent").inc()
        logger.info("Notified user %s that file=%s finished (%s)", uid, file_id, outcome)
    except Exception as e:  # noqa: BLE001 — notification must never fail the task
        metrics.CONVERSION_NOTIFICATIONS.labels(outcome="failed").inc()
        logger.warning(
            "Could not notify user %s about file=%s (%s): %s", user_id, file_id, outcome, e
        )


def _refund_pages(user_id: str, pages: int | None, reserved_day: str | None = None) -> None:
    """Give a failed conversion's reserved pages back to the user's daily quota.

    The refund must target the day the pages were *reserved* on, not the day the
    refund happens. A task submitted at 23:59 and failing at 00:00 used to credit
    the new day's counter, zeroing a fresh allowance and handing out free pages —
    repeatable nightly. When the row for that day is gone the UPDATE matches
    nothing and the refund is silently lost, so the outcome is counted either way.
    """
    if not pages or user_id.startswith("trial/") or not settings.DATABASE_URL:
        return
    try:
        from datetime import date

        from app.db.session import get_engine
        from app.services import quota

        day = date.fromisoformat(reserved_day) if reserved_day else None
        quota.release(get_engine(), int(user_id), pages, day=day)
        metrics.REFUNDS.labels(outcome="ok").inc()
        logger.info("Refunded %d pages to user %s for %s", pages, user_id, day or "today")
    except Exception as e:  # noqa: BLE001
        # Counted, not just logged: a silent refund outage is how users get charged
        # for failures nobody hears about.
        metrics.REFUNDS.labels(outcome="failed").inc()
        logger.error("Failed to refund %s pages to user %s: %s", pages, user_id, e)


def process_task(task: dict, redelivered: bool = False) -> None:
    file_id = task.get("file_id")
    user_id = task.get("user_id")
    mode = task.get("mode", "ocr")
    max_pages = task.get("max_pages")  # set for anonymous trials (first page only)
    pages = task.get("pages")          # reserved page count, for refund on failure

    if not file_id or not user_id:
        logger.error("Task missing file_id or user_id: %s", task)
        return

    storage = get_storage()
    if redelivered:
        # A redelivery whose status is already terminal was fully handled by a previous
        # attempt (incl. the quota refund); running it again would double-refund and
        # re-burn Gemini quota. Only a crash mid-task ("processing") warrants a retry.
        try:
            prior = storage.get_status(user_id, file_id)
        except Exception:  # noqa: BLE001
            prior = None
        if prior in ("done", "failed"):
            logger.warning("Skipping redelivered task file=%s user=%s: already %s", file_id, user_id, prior)
            return
    storage.set_status(user_id, file_id, "processing")
    logger.info(
        "Processing file=%s user=%s mode=%s backend=%s max_pages=%s",
        file_id, user_id, mode, OCR_BACKEND, max_pages,
    )
    t0 = time.perf_counter()
    outcome = "failed"
    reason: str | None = None

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
            docx_bytes = _call_gemini(pdf_bytes, max_pages, mode)

        # ── Blank-output guard ──────────────────────────────────────────────
        # An image-only scan makes every page come back empty, and an empty DOCX is
        # still a valid ~36KB file. Reporting that as "done" spends the user's quota
        # on a Word document with zero readable characters — the single most likely
        # way for someone to conclude the product is broken. Check before saving so
        # no blank artefact is stored at all.
        #
        # The rule is document-wide, not per page, and that is the whole point: a
        # title page, a blank verso or a full-page figure in the middle of a book is
        # normal and must not throw away the 39 good pages around it. What is never
        # legitimate is a document in which *nothing* was recognised.
        visible = _docx_visible_chars(docx_bytes)
        if visible is not None and visible < settings.OCR_MIN_OUTPUT_CHARS:
            raise EmptyOcrResult(visible, len(docx_bytes))

        # ── Save DOCX back to storage ───────────────────────────────────────
        stem = file_id.rsplit(".", 1)[0]
        docx_filename = f"{stem}.docx"
        storage.save_file(user_id, docx_filename, io.BytesIO(docx_bytes))
        logger.info("Saved DOCX as %s", docx_filename)

        storage.set_status(user_id, file_id, "done")
        logger.info("file=%s marked as done", file_id)
        outcome = "done"
        metrics.OCR_REQUESTS.labels(status="success", mode=mode).inc()
        metrics.OCR_REQUEST_DURATION.labels(mode=mode).observe(time.perf_counter() - t0)

    except EmptyOcrResult as e:
        # Counted as "empty", not "error": from the dashboard, "we are handing back
        # blank documents" and "the pipeline is throwing" need to be separable.
        # NB: the literal "Failed to process file=" text is matched by a Grafana/Loki
        # panel, so this stays on that panel too — it is a failed conversion.
        logger.error(
            "Failed to process file=%s: no readable text. %d visible character(s) "
            "(minimum %d) in %d bytes of DOCX; user=%s mode=%s max_pages=%s "
            "reserved_pages=%s pdf_bytes=%d. Likely an image-only scan or a total "
            "OCR miss — refusing to report a blank document as done.",
            file_id, e.visible_chars, settings.OCR_MIN_OUTPUT_CHARS, e.docx_bytes,
            user_id, mode, max_pages, pages, len(pdf_bytes),
        )
        storage.set_status(user_id, file_id, "failed")
        reason = "no_text"
        metrics.OCR_REQUESTS.labels(status="empty", mode=mode).inc()
        metrics.OCR_REQUEST_DURATION.labels(mode=mode).observe(time.perf_counter() - t0)
        _refund_pages(user_id, pages, task.get("reserved_day"))

    except Exception as e:
        # NB: the literal "Failed to process file=" text is matched by a Grafana/Loki panel.
        logger.error("Failed to process file=%s: %s", file_id, e, exc_info=True)
        storage.set_status(user_id, file_id, "failed")
        reason = "error"
        metrics.OCR_REQUESTS.labels(status="error", mode=mode).inc()
        metrics.OCR_REQUEST_DURATION.labels(mode=mode).observe(time.perf_counter() - t0)
        _refund_pages(user_id, pages, task.get("reserved_day"))

    # Deliberately outside every handler: a conversion that succeeded must stay
    # succeeded, so nothing raised in here can reach the "failed" path above.
    _notify_conversion_finished(
        user_id, file_id, outcome, time.perf_counter() - t0, pages=pages, reason=reason,
    )


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


def _make_callback(connection):
    def callback(ch, method, properties, body):
        # A task can block for minutes (Gemini 429 backoff), far longer than the
        # AMQP heartbeat. Run it on a thread so start_consuming() keeps servicing
        # heartbeats; otherwise RabbitMQ drops us, redelivers the message and the
        # same document loops forever. (pika's basic_consumer_threaded pattern;
        # prefetch=1 keeps processing serial.)
        def work():
            try:
                process_task(json.loads(body), redelivered=method.redelivered)
            except Exception as e:  # noqa: BLE001
                logger.error("Unhandled error processing message: %s", e)
            finally:
                connection.add_callback_threadsafe(
                    lambda: ch.basic_ack(delivery_tag=method.delivery_tag)
                )

        threading.Thread(target=work, name="ocr-task", daemon=True).start()

    return callback


def consume() -> None:
    while True:
        connection = _connect()
        try:
            channel = connection.channel()
            try:
                declare_task_queue(channel, settings.rabbitmq_queue)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Could not declare %s with delivery limits (%s) — falling back to "
                    "the existing queue. A poison message will still loop until the "
                    "queue is migrated.",
                    settings.rabbitmq_queue, e,
                )
                channel = connection.channel()
                channel.basic_qos(prefetch_count=1)
                channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)
            channel.basic_qos(prefetch_count=1)
            logger.info("Waiting for messages in '%s'. CTRL+C to exit.", settings.rabbitmq_queue)

            channel.basic_consume(queue=settings.rabbitmq_queue, on_message_callback=_make_callback(connection))

            # Re-arms itself on the connection's I/O loop; stops being refreshed the
            # moment start_consuming() returns or the connection dies.
            def _beat():
                touch_heartbeat()
                connection.call_later(_HEARTBEAT_INTERVAL_S, _beat)

            _beat()

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


def main() -> None:
    # Start /metrics first so the pod is scrapeable even while RabbitMQ is unreachable.
    metrics.start_worker_metrics_server(settings.WORKER_METRICS_PORT)
    consume()


if __name__ == "__main__":
    main()

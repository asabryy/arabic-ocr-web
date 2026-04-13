"""
Textara OCR — local dev HTTP server
====================================
Wraps pipeline.py. Loads the Qari model eagerly at startup.

Endpoints:
  POST /process   — upload PDF, receive DOCX bytes
  GET  /metrics   — Prometheus metrics
  GET  /stats     — JSON stats summary
  GET  /health    — liveness check

Usage:
    cd ocr-worker
    uvicorn local_app:app --host 0.0.0.0 --port 8002
"""

import io
import time
import logging
import tempfile
import pathlib
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response, JSONResponse
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST,
)

import pipeline as ocr

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("textara-ocr")

# ── Prometheus metrics ────────────────────────────────────────────────────────

REQUEST_TOTAL = Counter(
    "ocr_requests_total",
    "Total OCR requests by outcome",
    ["status"],          # "success" | "error"
)
PAGE_TOTAL = Counter(
    "ocr_pages_total",
    "Total pages processed",
)
REQUEST_DURATION = Histogram(
    "ocr_request_duration_seconds",
    "End-to-end request processing time (seconds)",
    buckets=[2, 5, 10, 30, 60, 120, 300, 600],
)
PAGE_DURATION = Histogram(
    "ocr_page_duration_seconds",
    "Per-page Qari OCR time (seconds)",
    buckets=[0.5, 1, 2, 3, 5, 10, 20, 40],
)
VRAM_USED = Gauge(
    "ocr_vram_used_bytes",
    "Current GPU VRAM allocated (bytes)",
)
VRAM_TOTAL = Gauge(
    "ocr_vram_total_bytes",
    "Total GPU VRAM available (bytes)",
)
MODEL_LOAD_TIME = Gauge(
    "ocr_model_load_seconds",
    "Seconds taken to load the Qari model",
)
MODEL_READY = Gauge(
    "ocr_model_ready",
    "1 if the Qari model is loaded and ready, 0 otherwise",
)

# ── Runtime state ─────────────────────────────────────────────────────────────

_model     = None
_processor = None

_stats = {
    "requests": {"total": 0, "success": 0, "error": 0},
    "pages":    {"total": 0},
    "timing":   {"total_page_seconds": 0.0, "total_request_seconds": 0.0},
    "model":    {"loaded": False, "load_time_seconds": None},
}

# ── Startup / shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model, _processor

    MODEL_READY.set(0)
    log.info("Loading Qari model at startup...")

    _model, _processor, load_time = ocr.load_model()

    _stats["model"]["loaded"]            = True
    _stats["model"]["load_time_seconds"] = round(load_time, 2)
    MODEL_LOAD_TIME.set(load_time)
    MODEL_READY.set(1)
    _update_vram_gauges()

    log.info(f"Qari model ready — load time {load_time:.1f}s")
    yield
    log.info("Server shutting down")


app = FastAPI(title="Textara OCR Dev Server", lifespan=lifespan)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _update_vram_gauges():
    if torch.cuda.is_available():
        VRAM_USED.set(torch.cuda.memory_allocated())
        VRAM_TOTAL.set(torch.cuda.get_device_properties(0).total_memory)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    """Accept a PDF upload, return DOCX bytes."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="PDF required")

    req_start = time.time()
    _stats["requests"]["total"] += 1
    log.info(f"Request — file={file.filename!r}")

    tmp_path = None
    try:
        pdf_bytes = await file.read()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = pathlib.Path(tmp.name)

        pdf_doc = ocr.open_pdf(tmp_path)
        n_pages = len(pdf_doc)
        log.info(f"  {n_pages} page(s) to process")

        pages_text = []
        for i, page in enumerate(pdf_doc, 1):
            log.info(f"  Page {i}/{n_pages} — rendering")
            img = ocr.render_page(page)
            text, page_elapsed, vram_delta = ocr.ocr_page(img, _model, _processor)
            pages_text.append(text)

            PAGE_DURATION.observe(page_elapsed)
            PAGE_TOTAL.inc()
            _stats["pages"]["total"] += 1
            _stats["timing"]["total_page_seconds"] += page_elapsed

            log.info(
                f"  Page {i}/{n_pages} done — "
                f"{page_elapsed:.2f}s | {len(text)} chars | "
                f"vram_delta={vram_delta/1e6:+.1f} MB"
            )

        pdf_doc.close()
        _update_vram_gauges()

        buf = io.BytesIO()
        ocr.build_docx(pages_text, buf)
        buf.seek(0)

        req_elapsed = time.time() - req_start
        REQUEST_DURATION.observe(req_elapsed)
        REQUEST_TOTAL.labels(status="success").inc()
        _stats["requests"]["success"] += 1
        _stats["timing"]["total_request_seconds"] += req_elapsed

        log.info(f"Request complete — {req_elapsed:.2f}s total ({n_pages} pages)")

        return Response(
            content=buf.read(),
            media_type=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
        )

    except Exception as e:
        req_elapsed = time.time() - req_start
        REQUEST_TOTAL.labels(status="error").inc()
        _stats["requests"]["error"] += 1
        log.error(f"Request failed after {req_elapsed:.2f}s — {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)


@app.get("/metrics")
def metrics():
    """Prometheus metrics — scrape this from Grafana/Prometheus."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats")
def stats():
    """JSON stats summary — quick human-readable overview."""
    total_pages = _stats["pages"]["total"]
    total_ok    = _stats["requests"]["success"]

    avg_page = (
        _stats["timing"]["total_page_seconds"] / total_pages
        if total_pages else None
    )
    avg_req = (
        _stats["timing"]["total_request_seconds"] / total_ok
        if total_ok else None
    )

    vram = {}
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        vram = {
            "device":   props.name,
            "used_gb":  round(torch.cuda.memory_allocated() / 1e9, 2),
            "total_gb": round(props.total_memory / 1e9, 2),
        }

    return JSONResponse({
        "requests": _stats["requests"],
        "pages":    {"total": total_pages},
        "timing": {
            "avg_page_seconds":    round(avg_page, 2) if avg_page is not None else None,
            "avg_request_seconds": round(avg_req,  2) if avg_req  is not None else None,
        },
        "vram":  vram,
        "model": _stats["model"],
    })


@app.get("/health")
def health():
    return {
        "status":       "ok",
        "model_loaded": _stats["model"]["loaded"],
    }

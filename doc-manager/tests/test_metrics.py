"""Business-metric counters. The registry is process-global, so every assertion is a delta."""

from prometheus_client import REGISTRY

from tests.conftest import make_pdf

BASE = "/api/doc-manager/v1"


def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def _upload(client, name, pages):
    r = client.post(f"{BASE}/upload", files={"file": (name, make_pdf(pages), "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()


def test_upload_counts(client):
    before = sample("textara_uploads_total")
    _upload(client, "a.pdf", 2)
    assert sample("textara_uploads_total") == before + 1


def test_convert_402_counts_quota_rejection(db_client):
    before = sample("textara_quota_rejections_total", reason="doc_pages_exceeded", plan="free")
    conv_before = sample("textara_conversions_requested_total", mode="ocr", plan="free")
    _upload(db_client, "big.pdf", 12)
    assert db_client.post(f"{BASE}/convert?filename=big.pdf").status_code == 402
    assert sample("textara_quota_rejections_total", reason="doc_pages_exceeded", plan="free") == before + 1
    assert sample("textara_conversions_requested_total", mode="ocr", plan="free") == conv_before


def test_convert_200_counts_conversion_and_pages(db_client, published):
    c0 = sample("textara_conversions_requested_total", mode="ocr", plan="free")
    p0 = sample("textara_pages_requested_total", mode="ocr", plan="free")
    _upload(db_client, "a.pdf", 4)
    assert db_client.post(f"{BASE}/convert?filename=a.pdf").status_code == 200
    assert sample("textara_conversions_requested_total", mode="ocr", plan="free") == c0 + 1
    assert sample("textara_pages_requested_total", mode="ocr", plan="free") == p0 + 4


def test_convert_enqueue_failure_counts(db_client, monkeypatch):
    def boom(_):
        raise RuntimeError("rabbit down")

    monkeypatch.setattr("app.api.api_v1.endpoints.document.publish_task", boom)
    before = sample("textara_enqueue_failures_total", mode="ocr")
    _upload(db_client, "a.pdf", 1)
    assert db_client.post(f"{BASE}/convert?filename=a.pdf").status_code == 503
    assert sample("textara_enqueue_failures_total", mode="ocr") == before + 1


def test_trial_counts_starts_pages_and_rate_limit(client):
    c0 = sample("textara_conversions_requested_total", mode="trial", plan="anonymous")
    p0 = sample("textara_pages_requested_total", mode="trial", plan="anonymous")
    r0 = sample("textara_trial_rejections_total", reason="rate_limited")
    for _ in range(3):
        assert client.post(f"{BASE}/trial", files={"file": ("r.pdf", make_pdf(5), "application/pdf")}).status_code == 202
    assert client.post(f"{BASE}/trial", files={"file": ("r.pdf", make_pdf(5), "application/pdf")}).status_code == 429
    assert sample("textara_conversions_requested_total", mode="trial", plan="anonymous") == c0 + 3
    assert sample("textara_pages_requested_total", mode="trial", plan="anonymous") == p0 + 3  # 1 page each
    assert sample("textara_trial_rejections_total", reason="rate_limited") == r0 + 1


def test_trial_rejection_reasons(client, monkeypatch):
    inv0 = sample("textara_trial_rejections_total", reason="invalid_pdf")
    assert client.post(f"{BASE}/trial", files={"file": ("x.pdf", b"nope", "application/pdf")}).status_code == 400
    assert sample("textara_trial_rejections_total", reason="invalid_pdf") == inv0 + 1

    monkeypatch.setattr("app.core.config.settings.TRIAL_MAX_UPLOAD_MB", 0)
    big0 = sample("textara_trial_rejections_total", reason="too_large")
    assert client.post(f"{BASE}/trial", files={"file": ("r.pdf", make_pdf(1), "application/pdf")}).status_code == 413
    assert sample("textara_trial_rejections_total", reason="too_large") == big0 + 1


def test_trial_download_counts(client, storage):
    import io

    tid = client.post(f"{BASE}/trial", files={"file": ("r.pdf", make_pdf(1), "application/pdf")}).json()["trial_id"]
    owner = f"trial/{tid}"
    storage.save_file(owner, "document.docx", io.BytesIO(b"PK\x03\x04x"))
    storage.set_status(owner, "document.pdf", "done")
    before = sample("textara_trial_downloads_total")
    assert client.get(f"{BASE}/trial/{tid}/download").status_code == 200
    assert sample("textara_trial_downloads_total") == before + 1


def test_health_and_metrics_excluded_from_http_metrics(client):
    for _ in range(2):
        assert client.get(f"{BASE}/health").status_code == 200
    body = client.get("/metrics").text
    assert 'handler="/api/doc-manager/v1/health"' not in body
    assert 'handler="/metrics"' not in body
    # sanity: a real route is still instrumented
    client.get(f"{BASE}/trial/{'0' * 32}/status")
    assert "http_requests_total" in client.get("/metrics").text

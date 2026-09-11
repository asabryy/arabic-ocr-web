import io

from tests.conftest import make_pdf

BASE = "/api/doc-manager/v1/trial"


def _start(client, pages=7, name="report.pdf"):
    return client.post(BASE, files={"file": (name, make_pdf(pages), "application/pdf")})


def test_start_trial_202_stores_and_queues_first_page_only(client, published, storage):
    r = _start(client)
    assert r.status_code == 202, r.text
    body = r.json()
    tid = body["trial_id"]
    assert len(tid) == 32 and body["pages_total"] == 7 and body["max_pages"] == 1
    assert body["status"] == "processing"

    owner = f"trial/{tid}"
    assert storage.file_exists(owner, "document.pdf")
    assert storage.get_status(owner, "document.pdf") == "processing"
    assert storage.get_meta(owner, "document.pdf") == {
        "pages": 7, "original_name": "report.pdf", "max_pages": 1,
    }
    assert published == [
        {"file_id": "document.pdf", "user_id": owner, "mode": "trial", "max_pages": 1}
    ]


def test_trial_status_and_download_lifecycle(client, storage):
    tid = _start(client).json()["trial_id"]
    owner = f"trial/{tid}"

    assert client.get(f"{BASE}/{tid}/status").json()["status"] == "processing"
    assert client.get(f"{BASE}/{tid}/download").status_code == 409  # not done yet

    # Simulate the worker finishing.
    storage.save_file(owner, "document.docx", io.BytesIO(b"PK\x03\x04docx-bytes"))
    storage.set_status(owner, "document.pdf", "done")

    assert client.get(f"{BASE}/{tid}/status").json()["status"] == "done"
    r = client.get(f"{BASE}/{tid}/download")
    assert r.status_code == 200
    assert r.content == b"PK\x03\x04docx-bytes"
    assert "report.docx" in r.headers["content-disposition"]


def test_trial_unknown_or_malformed_id_404(client):
    assert client.get(f"{BASE}/{'0' * 32}/status").status_code == 404
    assert client.get(f"{BASE}/not-a-uuid/status").status_code == 404
    assert client.get(f"{BASE}/../1/status").status_code in (404, 422)


def test_trial_rejects_non_pdf(client):
    r = client.post(BASE, files={"file": ("x.pdf", b"nope", "application/pdf")})
    assert r.status_code == 400


def test_trial_rejects_oversize(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.TRIAL_MAX_UPLOAD_MB", 0)
    assert _start(client).status_code == 413


def test_trial_ip_rate_limit_429(client):
    # Default limit is 3/day per client IP.
    for _ in range(3):
        assert _start(client).status_code == 202
    r = _start(client)
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "trial_limit_exceeded"


def test_trial_rate_limit_is_per_forwarded_ip(client):
    for _ in range(3):
        assert _start(client).status_code == 202
    assert _start(client).status_code == 429
    # A different client behind the ingress gets its own budget.
    r = client.post(
        BASE,
        files={"file": ("r.pdf", make_pdf(1), "application/pdf")},
        headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.1"},
    )
    assert r.status_code == 202


def test_trial_publish_failure_cleans_up(client, monkeypatch, storage):
    def boom(_):
        raise RuntimeError("rabbit down")

    monkeypatch.setattr("app.api.api_v1.endpoints.trial.publish_task", boom)
    r = _start(client)
    assert r.status_code == 503
    # Nothing left behind under any trial/ owner.
    import os

    from app.core.config import settings

    trial_root = os.path.join(settings.UPLOAD_DIR, "trial")
    leftovers = [
        f for d in (os.listdir(trial_root) if os.path.isdir(trial_root) else [])
        for f in os.listdir(os.path.join(trial_root, d))
    ]
    assert leftovers == []

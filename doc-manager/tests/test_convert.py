import io

from sqlalchemy import text

from app.services import quota
from tests.conftest import make_pdf

BASE = "/api/doc-manager/v1"


def _upload(client, name, pages):
    r = client.post(f"{BASE}/upload", files={"file": (name, make_pdf(pages), "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()


def test_upload_reports_page_count_and_persists_meta(client, storage):
    body = _upload(client, "three.pdf", 3)
    assert body["pages"] == 3 and body["status"] == "pending"
    assert storage.get_meta("1", "three.pdf") == {"pages": 3}


def test_upload_rejects_non_pdf(client):
    r = client.post(f"{BASE}/upload", files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 400


def test_convert_missing_file_404(db_client):
    assert db_client.post(f"{BASE}/convert?filename=nope.pdf").status_code == 404


def test_convert_success_reserves_and_publishes(db_client, published, db):
    _upload(db_client, "a.pdf", 4)
    r = db_client.post(f"{BASE}/convert?filename=a.pdf")
    assert r.status_code == 200, r.text
    body = r.json()
    # A document inside the per-document cap is untouched by partial conversion:
    # same reservation, same task, same output name, and nothing marked partial.
    assert {k: body[k] for k in ("filename", "status", "pages", "used_today", "daily_limit")} == {
        "filename": "a.pdf", "status": "processing", "pages": 4,
        "used_today": 4, "daily_limit": 10,
    }
    assert body["partial"] is False
    assert body["output_filename"] == "a.docx" and body["part_filename"] is None
    assert body["remaining_pages"] == 0 and body["next_start_page"] is None
    assert len(published) == 1
    task = published[0]
    assert {k: task[k] for k in ("file_id", "user_id", "mode", "pages")} == {
        "file_id": "a.pdf", "user_id": "1", "mode": "ocr", "pages": 4,
    }
    # The whole-document message is unchanged: no new keys reach a worker that has
    # no reason to look at them.
    assert set(task) == {"file_id", "user_id", "mode", "pages", "reserved_day"}
    # The reservation day travels with the task so a refund lands on the row the
    # pages were taken from, not on whatever day the failure happens to occur.
    assert task["reserved_day"] == quota.today().isoformat()
    assert quota.used_today(db, 1) == 4


def test_convert_daily_limit_402_after_exhaustion(db_client):
    for i in range(10):
        _upload(db_client, f"p{i}.pdf", 1)
        assert db_client.post(f"{BASE}/convert?filename=p{i}.pdf").status_code == 200
    _upload(db_client, "one_more.pdf", 1)
    r = db_client.post(f"{BASE}/convert?filename=one_more.pdf")
    assert r.status_code == 402
    d = r.json()["detail"]
    assert d["code"] == "daily_pages_exceeded" and d["used"] == 10 and d["limit"] == 10


def test_convert_pro_plan_gets_pro_limits(db_client, current_user, db):
    pro = quota.limits_for("pro")
    current_user.id = "2"  # pro
    # Comfortably inside both caps, and larger than the free plan would allow.
    _upload(db_client, "big.pdf", pro.max_doc_pages - 1)
    assert db_client.post(f"{BASE}/convert?filename=big.pdf").status_code == 200

    # A fresh day, so what is being tested is the per-document cap and not the
    # daily budget the previous document just spent.
    with db.begin() as conn:
        conn.execute(text("TRUNCATE usage_daily"))

    # Over the Pro per-document cap: converted in a batch of exactly that cap,
    # not refused.
    _upload(db_client, "huge.pdf", pro.max_doc_pages + 1)
    r = db_client.post(f"{BASE}/convert?filename=huge.pdf")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["partial"] is True and body["pages"] == pro.max_doc_pages
    assert body["end_page"] == pro.max_doc_pages
    assert body["next_start_page"] == pro.max_doc_pages + 1
    assert body["remaining_pages"] == 1


def test_convert_publish_failure_releases_reservation(db_client, monkeypatch, db):
    def boom(_):
        raise RuntimeError("rabbit down")

    monkeypatch.setattr("app.api.api_v1.endpoints.document.publish_task", boom)
    _upload(db_client, "a.pdf", 3)
    assert db_client.post(f"{BASE}/convert?filename=a.pdf").status_code == 503
    assert quota.used_today(db, 1) == 0


def test_convert_backfills_missing_meta(db_client, storage, db):
    # Simulate a file uploaded before page counting existed: no .meta.json sidecar.
    storage.save_file("1", "legacy.pdf", io.BytesIO(make_pdf(2)))
    assert storage.get_meta("1", "legacy.pdf") == {}
    r = db_client.post(f"{BASE}/convert?filename=legacy.pdf")
    assert r.status_code == 200 and r.json()["pages"] == 2
    # A whole-document conversion records no ranges: the file's own status is the
    # outcome, exactly as before partial conversion existed.
    assert storage.get_meta("1", "legacy.pdf") == {"pages": 2}


def test_usage_endpoint(db_client):
    _upload(db_client, "a.pdf", 3)
    db_client.post(f"{BASE}/convert?filename=a.pdf")
    r = db_client.get(f"{BASE}/usage")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "free" and body["used_today"] == 3
    assert body["daily_limit"] == 10 and body["max_doc_pages"] == 10
    assert body["resets_at"].endswith("+00:00")


def test_quota_endpoints_503_without_database(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.DATABASE_URL", "")
    assert client.get(f"{BASE}/usage").status_code == 503

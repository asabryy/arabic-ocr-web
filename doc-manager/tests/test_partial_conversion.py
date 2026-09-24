"""Partial conversion: a document longer than the plan's per-document cap.

Before this, 20 of the 41 documents authenticated users had ever uploaded were
refused outright with a 402 nobody could get past. These tests pin the way out:
a bounded batch is converted, the reservation matches the batch rather than the
book, each batch lands under its own name, and the resume point survives.
"""

from app.services import quota
from tests.conftest import make_pdf

BASE = "/api/doc-manager/v1"


def _upload(client, name, pages):
    r = client.post(f"{BASE}/upload", files={"file": (name, make_pdf(pages), "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()


def _pages_of(storage, owner, name):
    import fitz

    with open(storage.get_path(owner, name), "rb") as fh:
        doc = fitz.open(stream=fh.read(), filetype="pdf")
    try:
        return [doc[i].get_text().strip() for i in range(len(doc))]
    finally:
        doc.close()


# ── the headline case ────────────────────────────────────────────────────────

def test_over_cap_document_converts_a_bounded_batch(db_client, published, db, storage):
    _upload(db_client, "book.pdf", 25)  # free plan: 10 pages per document
    r = db_client.post(f"{BASE}/convert?filename=book.pdf")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["partial"] is True
    assert (body["start_page"], body["end_page"]) == (1, 10)
    assert body["pages"] == 10 and body["total_pages"] == 25
    assert body["remaining_pages"] == 15 and body["next_start_page"] == 11
    assert body["output_filename"] == "book__p1-10.docx"

    # Quota is charged for the 10 pages queued, not for the 25-page document.
    assert body["used_today"] == 10
    assert quota.used_today(db, 1) == 10

    task = published[0]
    assert task["file_id"] == "book__p1-10.pdf" and task["pages"] == 10
    # ...and that file really holds pages 1-10 of the book, so a worker running the
    # previously deployed image produces the right DOCX from this message alone.
    assert _pages_of(storage, "1", "book__p1-10.pdf") == [f"page {i}" for i in range(1, 11)]

    # Additive fields only; the old worker reads with .get() and ignores them.
    assert task["source_file_id"] == "book.pdf"
    assert (task["source_page_start"], task["source_page_end"]) == (1, 10)
    assert task["source_total_pages"] == 25
    assert set(task) >= {"file_id", "user_id", "mode", "pages", "reserved_day"}

    # The source document is not itself being converted and must not be left
    # sitting on "processing" forever; the batch carries the status.
    assert storage.get_status("1", "book.pdf") == "pending"
    assert storage.get_status("1", "book__p1-10.pdf") == "processing"


def test_resume_from_where_the_last_batch_stopped(db_client, published, db, storage):
    _upload(db_client, "book.pdf", 25)
    assert db_client.post(f"{BASE}/convert?filename=book.pdf").status_code == 200
    # New day, so the daily cap is not what is being tested here.
    storage.set_status("1", "book__p1-10.pdf", "done")
    with db.begin() as conn:
        from sqlalchemy import text
        conn.execute(text("TRUNCATE usage_daily"))

    r = db_client.post(f"{BASE}/convert?filename=book.pdf")
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["start_page"], body["end_page"]) == (11, 20)
    assert body["converted_pages"] == 20 and body["remaining_pages"] == 5
    assert body["next_start_page"] == 21
    assert body["output_filename"] == "book__p11-20.docx"

    # Distinct output names: the second batch does not overwrite the first.
    outputs = {p["output"] for p in storage.get_meta("1", "book.pdf")["ranges"]}
    assert outputs == {"book__p1-10.docx", "book__p11-20.docx"}
    assert published[-1]["file_id"] == "book__p11-20.pdf"
    assert _pages_of(storage, "1", "book__p11-20.pdf") == [f"page {i}" for i in range(11, 21)]


def test_last_batch_is_short_and_then_the_document_is_complete(db_client, db, storage):
    _upload(db_client, "book.pdf", 25)
    from sqlalchemy import text

    for expected in ((1, 10), (11, 20), (21, 25)):
        with db.begin() as conn:
            conn.execute(text("TRUNCATE usage_daily"))
        r = db_client.post(f"{BASE}/convert?filename=book.pdf")
        assert r.status_code == 200, r.text
        assert (r.json()["start_page"], r.json()["end_page"]) == expected

    with db.begin() as conn:
        conn.execute(text("TRUNCATE usage_daily"))
    r = db_client.post(f"{BASE}/convert?filename=book.pdf")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "already_converted"
    # Nothing was charged for the refused click.
    assert quota.used_today(db, 1) == 0


# ── explicit ranges ──────────────────────────────────────────────────────────

def test_explicit_range_is_honoured(db_client, db, storage):
    _upload(db_client, "book.pdf", 25)
    r = db_client.post(f"{BASE}/convert?filename=book.pdf&start_page=16&end_page=20")
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["start_page"], body["end_page"], body["pages"]) == (16, 20, 5)
    assert quota.used_today(db, 1) == 5
    assert _pages_of(storage, "1", "book__p16-20.pdf") == [f"page {i}" for i in range(16, 21)]


def test_explicit_range_longer_than_the_cap_is_clamped_not_refused(db_client, db):
    _upload(db_client, "book.pdf", 25)
    r = db_client.post(f"{BASE}/convert?filename=book.pdf&start_page=1&end_page=25")
    assert r.status_code == 200, r.text
    assert r.json()["end_page"] == 10 and r.json()["pages"] == 10
    assert quota.used_today(db, 1) == 10


def test_next_batch_stops_before_an_already_converted_run(db_client, db):
    _upload(db_client, "book.pdf", 25)
    assert db_client.post(
        f"{BASE}/convert?filename=book.pdf&start_page=6&end_page=9"
    ).status_code == 200
    from sqlalchemy import text

    with db.begin() as conn:
        conn.execute(text("TRUNCATE usage_daily"))
    r = db_client.post(f"{BASE}/convert?filename=book.pdf")
    # Pages 1-5 are the first gap; the batch stops at 5 rather than re-billing 6-9.
    assert (r.json()["start_page"], r.json()["end_page"]) == (1, 5)


def test_start_page_past_the_end_is_a_400(db_client):
    _upload(db_client, "book.pdf", 25)
    r = db_client.post(f"{BASE}/convert?filename=book.pdf&start_page=99")
    assert r.status_code == 400


def test_repeat_click_on_an_in_flight_batch_is_409(db_client, db):
    _upload(db_client, "book.pdf", 25)
    assert db_client.post(f"{BASE}/convert?filename=book.pdf&start_page=1").status_code == 200
    r = db_client.post(f"{BASE}/convert?filename=book.pdf&start_page=1")
    assert r.status_code == 409
    assert quota.used_today(db, 1) == 10  # not charged twice


# ── the daily cap now actually bites ─────────────────────────────────────────

def test_batch_that_does_not_fit_todays_budget_is_refused_and_recorded(db_client, db, attempts):
    _upload(db_client, "short.pdf", 4)
    assert db_client.post(f"{BASE}/convert?filename=short.pdf").status_code == 200
    _upload(db_client, "book.pdf", 25)
    r = db_client.post(f"{BASE}/convert?filename=book.pdf")  # wants 10, only 6 left
    assert r.status_code == 402
    d = r.json()["detail"]
    assert d["code"] == "daily_pages_exceeded" and d["used"] == 4 and d["limit"] == 10
    # The batch can still be taken at a size that fits.
    r = db_client.post(f"{BASE}/convert?filename=book.pdf&start_page=1&end_page=6")
    assert r.status_code == 200 and quota.used_today(db, 1) == 10

    rows = attempts()
    assert [row["outcome"] for row in rows] == [
        "accepted", "daily_pages_exceeded", "accepted",
    ]


# ── failures leave nothing behind ────────────────────────────────────────────

def test_publish_failure_releases_and_removes_the_batch(db_client, monkeypatch, db, storage):
    _upload(db_client, "book.pdf", 25)

    def boom(_):
        raise RuntimeError("rabbit down")

    monkeypatch.setattr("app.api.api_v1.endpoints.document.publish_task", boom)
    assert db_client.post(f"{BASE}/convert?filename=book.pdf").status_code == 503
    assert quota.used_today(db, 1) == 0
    assert not storage.file_exists("1", "book__p1-10.pdf")
    # No resume point pointing at a batch that was never queued.
    assert storage.get_meta("1", "book.pdf").get("ranges") in (None, [])


def test_deleting_the_document_takes_its_batches_with_it(db_client, storage):
    _upload(db_client, "book.pdf", 25)
    assert db_client.post(f"{BASE}/convert?filename=book.pdf").status_code == 200
    assert storage.file_exists("1", "book__p1-10.pdf")
    assert db_client.delete(f"{BASE}/documents?filename=book.pdf").status_code == 200
    assert not storage.file_exists("1", "book__p1-10.pdf")


def test_deleting_one_batch_reopens_those_pages(db_client, db, storage):
    _upload(db_client, "book.pdf", 25)
    assert db_client.post(f"{BASE}/convert?filename=book.pdf").status_code == 200
    assert db_client.delete(f"{BASE}/documents?filename=book__p1-10.pdf").status_code == 200
    assert storage.get_meta("1", "book.pdf")["ranges"] == []
    from sqlalchemy import text

    with db.begin() as conn:
        conn.execute(text("TRUNCATE usage_daily"))
    r = db_client.post(f"{BASE}/convert?filename=book.pdf")
    assert (r.json()["start_page"], r.json()["end_page"]) == (1, 10)


# ── progress endpoint (what the UI shows) ────────────────────────────────────

def test_conversion_progress_reports_what_is_done_and_what_is_next(db_client):
    _upload(db_client, "book.pdf", 25)
    _upload(db_client, "small.pdf", 3)
    assert db_client.post(f"{BASE}/convert?filename=book.pdf").status_code == 200

    r = db_client.get(f"{BASE}/conversion-progress")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["max_doc_pages"] == 10 and body["plan"] == "free"
    items = {i["filename"]: i for i in body["items"]}
    # The batch files are parts of a document, not documents of their own.
    assert set(items) == {"book.pdf", "small.pdf"}

    book = items["book.pdf"]
    assert book["total_pages"] == 25 and book["converted_pages"] == 10
    assert book["remaining_pages"] == 15 and book["next_start_page"] == 11
    assert book["ranges"] == [
        {"start": 1, "end": 10, "file": "book__p1-10.pdf", "output": "book__p1-10.docx"}
    ]
    assert items["small.pdf"]["partial"] is False

    one = db_client.get(f"{BASE}/conversion-progress?filename=book.pdf").json()
    assert one["items"] == [book]


def test_conversion_progress_404_for_an_unknown_file(db_client):
    assert db_client.get(f"{BASE}/conversion-progress?filename=nope.pdf").status_code == 404


# ── the durable record ───────────────────────────────────────────────────────

def test_attempts_record_the_batch_and_the_document_length(db_client, attempts):
    _upload(db_client, "book.pdf", 25)
    assert db_client.post(f"{BASE}/convert?filename=book.pdf").status_code == 200
    rows = attempts()
    assert len(rows) == 1
    assert rows[0] == {
        "user_id": 1, "pages": 10, "total_pages": 25,
        "start_page": 1, "end_page": 10, "outcome": "accepted", "plan": "free",
    }


def test_attempts_record_a_whole_document_conversion(db_client, attempts):
    _upload(db_client, "a.pdf", 4)
    assert db_client.post(f"{BASE}/convert?filename=a.pdf").status_code == 200
    assert attempts() == [{
        "user_id": 1, "pages": 4, "total_pages": 4,
        "start_page": 1, "end_page": 4, "outcome": "accepted", "plan": "free",
    }]


def test_attempts_record_an_enqueue_failure(db_client, monkeypatch, attempts):
    _upload(db_client, "a.pdf", 3)
    monkeypatch.setattr(
        "app.api.api_v1.endpoints.document.publish_task",
        lambda _: (_ for _ in ()).throw(RuntimeError("rabbit down")),
    )
    assert db_client.post(f"{BASE}/convert?filename=a.pdf").status_code == 503
    assert [r["outcome"] for r in attempts()] == ["enqueue_failed"]


def test_recording_failures_never_break_a_conversion(db_client, monkeypatch):
    _upload(db_client, "a.pdf", 3)

    def boom(*_a, **_k):
        raise RuntimeError("attempts table is gone")

    monkeypatch.setattr(quota.conversion_attempts, "insert", boom)
    assert db_client.post(f"{BASE}/convert?filename=a.pdf").status_code == 200


# ── downloads are counted ────────────────────────────────────────────────────

def test_download_increments_the_download_counter(db_client, storage):
    """Downloads are the moment the product delivers what the user came for, and
    were the one step of the funnel with no metric at all."""
    import io

    from app import metrics

    before = metrics.DOWNLOADS.labels(kind="docx")._value.get()
    storage.save_file("1", "a.docx", io.BytesIO(b"docx bytes"))
    assert db_client.get(f"{BASE}/download?filename=a.docx").status_code == 200
    assert metrics.DOWNLOADS.labels(kind="docx")._value.get() == before + 1

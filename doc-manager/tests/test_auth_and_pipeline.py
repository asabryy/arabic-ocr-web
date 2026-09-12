from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.config import settings
from app.dependencies.auth import get_current_user_id
from app.ocr import pipeline
from tests.conftest import make_pdf


def _token(**claims) -> str:
    payload = {"sub": "42", "exp": datetime.now(UTC) + timedelta(minutes=5), **claims}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def test_access_token_accepted():
    assert get_current_user_id(_token()) == "42"


def test_scoped_token_rejected():
    """Verification / reset tokens share the key but carry a scope — never valid as bearers."""
    for scope in ("email_verification", "password_reset"):
        with pytest.raises(HTTPException) as ex:
            get_current_user_id(_token(scope=scope))
        assert ex.value.status_code == 401


def test_token_without_sub_rejected():
    tok = jwt.encode({"exp": datetime.now(UTC) + timedelta(minutes=5)}, settings.SECRET_KEY,
                     algorithm=settings.ALGORITHM)
    with pytest.raises(HTTPException):
        get_current_user_id(tok)


def test_process_pdf_respects_max_pages(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "ocr_page", lambda png: (calls.append(png), "نص")[1])
    out = pipeline.process_pdf(make_pdf(3), max_pages=1)
    assert len(calls) == 1
    assert out[:2] == b"PK"  # a real DOCX (zip container)


def test_process_pdf_all_pages_by_default(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "ocr_page", lambda png: (calls.append(png), "x")[1])
    pipeline.process_pdf(make_pdf(3))
    assert len(calls) == 3


def test_process_pdf_max_pages_larger_than_doc(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "ocr_page", lambda png: (calls.append(png), "x")[1])
    pipeline.process_pdf(make_pdf(2), max_pages=10)
    assert len(calls) == 2


def test_process_pdf_records_page_metrics_by_mode(monkeypatch):
    from prometheus_client import REGISTRY

    monkeypatch.setattr(pipeline, "ocr_page", lambda png: "x")
    before = REGISTRY.get_sample_value("ocr_pages_total", {"mode": "trial"}) or 0.0
    hist_before = REGISTRY.get_sample_value("ocr_page_duration_seconds_count") or 0.0
    pipeline.process_pdf(make_pdf(3), max_pages=1, mode="trial")
    assert REGISTRY.get_sample_value("ocr_pages_total", {"mode": "trial"}) == before + 1
    assert REGISTRY.get_sample_value("ocr_page_duration_seconds_count") == hist_before + 1

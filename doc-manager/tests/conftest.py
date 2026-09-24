"""Shared fixtures.

DB-backed tests need a real Postgres (the atomic reserve relies on
`INSERT ... ON CONFLICT DO UPDATE ... WHERE` row-locking semantics that SQLite
can't emulate). Set TEST_DATABASE_URL to enable them; they are skipped otherwise.
Everything else (trial endpoint, auth dependency, pipeline, storage) runs with
LocalFileStorage on a temp dir and no database.
"""

import os

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core import config as config_module
from app.core.rate_limit import limiter
from app.db.session import get_engine
from app.db.tables import metadata
from app.dependencies.auth import get_current_user_id
from app.dependencies.storage import get_storage
from app.main import app
from app.models import conversion_attempt  # noqa: F401  # registers its table on `metadata`
from app.services.local_storage import LocalFileStorage

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def make_pdf(n_pages: int) -> bytes:
    doc = fitz.open()
    for i in range(n_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"page {i + 1}")
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.settings, "UPLOAD_DIR", str(tmp_path))
    return LocalFileStorage()


class CurrentUser:
    """Mutable holder so a test can switch the authenticated user id."""

    id = "1"


@pytest.fixture
def current_user():
    CurrentUser.id = "1"
    return CurrentUser


@pytest.fixture
def published(monkeypatch):
    """Capture publish_task calls instead of touching RabbitMQ."""
    calls: list[dict] = []
    monkeypatch.setattr("app.api.api_v1.endpoints.document.publish_task", calls.append)
    monkeypatch.setattr("app.api.api_v1.endpoints.trial.publish_task", calls.append)
    return calls


@pytest.fixture
def client(storage, current_user, published):
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_current_user_id] = lambda: CurrentUser.id
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_storage, None)
    app.dependency_overrides.pop(get_current_user_id, None)


# ── database-backed fixtures ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — skipping Postgres-backed tests")
    eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    metadata.drop_all(eng)
    metadata.create_all(eng)
    yield eng
    metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine):
    """Fresh state per test: seed a free user (1) and a pro user (2)."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE conversion_attempts, usage_daily, users"))
        conn.execute(text("INSERT INTO users (id, plan) VALUES (1, 'free'), (2, 'pro')"))
    return engine


@pytest.fixture
def db_client(client, db):
    app.dependency_overrides[get_engine] = lambda: db
    yield client
    app.dependency_overrides.pop(get_engine, None)


@pytest.fixture
def attempts(db):
    """Rows written to conversion_attempts, oldest first."""

    def _read() -> list[dict]:
        with db.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT user_id, pages, total_pages, start_page, end_page, outcome, plan "
                    "FROM conversion_attempts ORDER BY id"
                )
            ).mappings()
            return [dict(r) for r in rows]

    return _read

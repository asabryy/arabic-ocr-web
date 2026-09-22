"""Auth-service test harness: SQLite in memory, no network, no Stripe.

DATABASE_URL/SECRET_KEY are set before importing app modules because
app.core.config.Settings requires them at import time.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core import stripe_client  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import billing, usage, user  # noqa: E402,F401  # register tables
from app.models.user import User  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def stripe_configured(monkeypatch):
    """Turn billing on with dummy credentials (no calls leave the process)."""
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "price_dummy")
    monkeypatch.setattr(settings, "STRIPE_PRODUCT_PRO", "")
    stripe_client.reset_stripe_client()
    yield
    stripe_client.reset_stripe_client()


@pytest.fixture
def make_user(db):
    def _make(email="a@example.com", plan="free", customer_id=None, sub_id=None):
        u = User(
            email=email,
            hashed_password=None,
            name="Test",
            email_verified=True,
            plan=plan,
            stripe_customer_id=customer_id,
            stripe_subscription_id=sub_id,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    return _make

"""Single StripeClient for the process.

The module-level `stripe.api_key = ...` pattern is deprecated in the current SDK, and
the bare `client.customers` accessors are deprecated in favour of `client.v1.*`.
"""
import logging

from stripe import StripeClient

from app.core.config import settings

logger = logging.getLogger("auth-service.stripe")

_client: StripeClient | None = None


def billing_enabled() -> bool:
    """False when no secret key is configured — the /billing routes 404 in that case."""
    return bool(settings.STRIPE_SECRET_KEY)


def get_stripe() -> StripeClient:
    """Lazily build the client so an unconfigured deployment can still boot."""
    global _client
    if _client is None:
        if not settings.STRIPE_SECRET_KEY:
            raise RuntimeError("STRIPE_SECRET_KEY is not set")
        _client = StripeClient(
            settings.STRIPE_SECRET_KEY,
            stripe_version=settings.STRIPE_API_VERSION,
        )
        logger.info("Stripe client initialised (api_version=%s)", settings.STRIPE_API_VERSION)
    return _client


def reset_stripe_client() -> None:
    """Drop the cached client. Used by tests that patch the key."""
    global _client
    _client = None

from pydantic import BaseModel


class CheckoutSessionOut(BaseModel):
    """The Stripe-hosted Checkout page to send the browser to."""

    url: str


class PortalSessionOut(BaseModel):
    """The Stripe-hosted Customer Portal page (manage card, cancel, invoices)."""

    url: str

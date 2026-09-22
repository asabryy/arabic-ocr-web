import { authApi } from "../features/auth/authservice";

/**
 * Start a Pro subscription. Returns the Stripe-hosted Checkout URL to send the
 * browser to — the plan only changes once Stripe's webhook confirms payment.
 */
export const createCheckoutSession = async () => {
  const res = await authApi.post("/billing/checkout-session");
  return res.data.url;
};

/** Stripe Customer Portal: update card, view invoices, cancel. */
export const createPortalSession = async () => {
  const res = await authApi.post("/billing/portal-session");
  return res.data.url;
};

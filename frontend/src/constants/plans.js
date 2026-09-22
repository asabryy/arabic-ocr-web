// Plan identifiers shared by the pricing page, usage meter and limit modal.
// Upgrading is an action, not a route: see hooks/useUpgrade.js, which mints a Stripe
// Checkout Session and hands the browser to Stripe's hosted page.
export const PLAN_FREE = "free";
export const PLAN_PRO = "pro";

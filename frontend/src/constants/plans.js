// Plan identifiers shared by the pricing page, usage meter and limit modal.
// Upgrading is an action, not a route: see hooks/useUpgrade.js, which mints a Stripe
// Checkout Session and hands the browser to Stripe's hosted page.
export const PLAN_FREE = "free";
export const PLAN_PRO = "pro";
// Comped / beta accounts. Granted by hand through the admin API, never purchasable,
// so it must never appear in the pricing page or any upgrade path.
export const PLAN_UNLIMITED = "unlimited";

/** Plans that already have everything — nothing to upsell them. */
export const isPaidPlan = (plan) => plan === PLAN_PRO || plan === PLAN_UNLIMITED;

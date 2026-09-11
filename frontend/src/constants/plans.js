// The single seam for self-serve billing. When Stripe Checkout lands, point this at
// the checkout route; every "Upgrade" CTA (pricing page, limit modal) imports it.
export const UPGRADE_PATH = "/coming-soon";

export const PLAN_FREE = "free";
export const PLAN_PRO = "pro";

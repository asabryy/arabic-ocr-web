import { useState } from "react";
import { createCheckoutSession } from "../api/billing";

/**
 * The single "start paying" action, shared by every Upgrade CTA (pricing page,
 * limit modal, usage meter). Replaces the old UPGRADE_PATH link target: there is no
 * upgrade *page* — we mint a Checkout Session and hand the browser to Stripe.
 */
export function useUpgrade() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const startUpgrade = async () => {
    setLoading(true);
    setError("");
    try {
      const url = await createCheckoutSession();
      // Full navigation, not react-router — Checkout is on Stripe's domain.
      window.location.assign(url);
    } catch (err) {
      // 409 means a webhook already made them Pro; a reload will show the new plan.
      setError(err?.response?.status === 409 ? "already_pro" : "failed");
      setLoading(false);
    }
  };

  return { startUpgrade, loading, error };
}

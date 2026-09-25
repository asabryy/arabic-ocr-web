import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { CheckCircle2, Loader2 } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { isPaidPlan } from "../constants/plans";

// Stripe redirects here the moment checkout completes, but the plan is granted by the
// webhook, which may land a beat later. So poll /users/me rather than trusting the
// redirect — the webhook stays the single source of truth.
const POLL_MS = 1500;
const MAX_POLLS = 12; // ~18s

function BillingSuccess() {
  const { t } = useTranslation();
  const { user, login } = useAuth();
  const [timedOut, setTimedOut] = useState(false);
  const isPro = isPaidPlan(user?.plan);

  // A ref, not a local: `login` identity changes re-run this effect, which used to
  // reset a local counter to zero every tick — so MAX_POLLS was unreachable and a
  // customer whose webhook was slow watched the spinner forever.
  const polls = useRef(0);

  useEffect(() => {
    if (isPro) return undefined;
    const token = localStorage.getItem("access_token");
    const id = setInterval(async () => {
      polls.current += 1;
      if (polls.current > MAX_POLLS) {
        clearInterval(id);
        setTimedOut(true);
        return;
      }
      try {
        await login(token); // refreshes the user (and its plan) from /users/me
      } catch {
        /* keep polling — a transient failure shouldn't end the wait */
      }
    }, POLL_MS);
    return () => clearInterval(id);
  }, [isPro, login]);

  return (
    <div className="max-w-lg mx-auto py-16 text-center animate-fade-in">
      {isPro ? (
        <>
          <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-500 mb-4" />
          <h1 className="text-xl font-semibold mb-2">{t("billing.success.title")}</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">
            {t("billing.success.body")}
          </p>
          <Link to="/convert" className="btn-primary px-6 py-2">
            {t("billing.success.cta")}
          </Link>
        </>
      ) : (
        <>
          {!timedOut && <Loader2 className="w-8 h-8 mx-auto text-indigo-500 animate-spin mb-4" />}
          <h1 className="text-xl font-semibold mb-2">
            {timedOut ? t("billing.pending.title") : t("billing.confirming.title")}
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">
            {timedOut ? t("billing.pending.body") : t("billing.confirming.body")}
          </p>
          <Link to="/dashboard" className="btn-secondary px-6 py-2">
            {t("billing.backToDashboard")}
          </Link>
        </>
      )}
    </div>
  );
}

export default BillingSuccess;

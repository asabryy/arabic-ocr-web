import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Check } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { PLAN_PRO } from "../constants/plans";
import { useUpgrade } from "../hooks/useUpgrade";

const PLANS = [
  { id: "free", price: "$0",    accent: false, features: ["daily", "perDoc", "trial"] },
  { id: "pro",  price: "$9.99", accent: true,  features: ["daily", "perDoc", "priority"], period: true },
];

/**
 * CTA per plan card depends on who's looking:
 *  - anonymous → open the signup modal (props come from Routes)
 *  - free user  → Free card is "current"; Pro card goes to the upgrade seam
 *  - pro user   → Pro card is "current"
 */
function PlanCta({ plan, user, openRegister }) {
  const { t } = useTranslation();
  const { startUpgrade, loading, error } = useUpgrade();
  const cls = plan.accent ? "btn-primary justify-center py-2.5" : "btn-secondary justify-center py-2.5";
  const currentPlan = user?.plan === PLAN_PRO ? PLAN_PRO : "free";

  if (!user) {
    return (
      <button onClick={openRegister} className={cls}>
        {t("pricing.cta.getStarted")}
      </button>
    );
  }
  if (plan.id === currentPlan) {
    return (
      <span className="btn-secondary justify-center py-2.5 opacity-60 cursor-default">
        {t("pricing.cta.current")}
      </span>
    );
  }
  if (plan.id === PLAN_PRO) {
    return (
      <>
        <button onClick={startUpgrade} disabled={loading} className={cls}>
          {loading ? t("billing.redirecting") : t("pricing.cta.upgrade")}
        </button>
        {error && (
          <p className="text-xs text-red-500 mt-2 text-center">
            {t(error === "already_pro" ? "billing.errors.alreadyPro" : "billing.errors.failed")}
          </p>
        )}
      </>
    );
  }
  return null; // pro user looking at the free card
}

export default function PricingPage({ openRegister }) {
  const { t } = useTranslation();
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-4xl mx-auto px-6 py-20">
        <div className="mb-14">
          <div className="flex items-baseline gap-4 mb-6">
            <span className="section-label">{t("pricing.label")}</span>
            <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight mb-3 text-foreground">{t("pricing.title")}</h1>
          <p className="text-zinc-500 dark:text-zinc-400 text-sm max-w-md">{t("pricing.subtitle")}</p>
        </div>

        <div className="grid sm:grid-cols-2 gap-0 border border-zinc-200 dark:border-zinc-800 divide-y sm:divide-y-0 sm:divide-x divide-zinc-200 dark:divide-zinc-800">
          {PLANS.map((plan) => (
            <div key={plan.id} className={`p-8 flex flex-col bg-surface ${plan.accent ? "border-t-2 border-t-indigo-500" : "border-t-2 border-t-zinc-200 dark:border-t-zinc-700"}`}>
              <div className="mb-6">
                <h2 className="text-lg font-bold mb-1 text-foreground">{t(`plans.${plan.id}`)}</h2>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">{t(`pricing.${plan.id}.desc`)}</p>
              </div>
              <div className="mb-8">
                <span className="text-4xl font-extrabold tabular-nums text-foreground">{plan.price}</span>
                {plan.period && <span className="text-sm text-zinc-400 ms-1">{t("pricing.perMonth")}</span>}
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-zinc-600 dark:text-zinc-400">
                    <Check className="w-3.5 h-3.5 shrink-0 mt-0.5 text-indigo-500" />
                    {t(`pricing.${plan.id}.features.${f}`)}
                  </li>
                ))}
              </ul>
              <PlanCta plan={plan} user={user} openRegister={openRegister} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

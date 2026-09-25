import React from "react";
import { useTranslation } from "react-i18next";
import { Gauge, ExternalLink } from "lucide-react";
import Modal from "../ui/Modal";
import { isPaidPlan } from "../../constants/plans";
import { useUpgrade } from "../../hooks/useUpgrade";

/**
 * Shown when the API answers 402 with a plan-quota detail
 * ({code, message, limit, used, plan}). Mounted once in Routes and driven by
 * the onQuotaExceeded event from the API client.
 *
 * Three things this modal used to get wrong:
 *  - For an over-long document it said the plan allows N per document and offered
 *    Pro, which for a 300-page book fails in exactly the same way. Long documents
 *    now convert a batch at a time, so the copy says that instead of dead-ending.
 *  - "See Pro plan" did not see a plan: `startUpgrade` navigates straight to
 *    Stripe's card form. The label now says what the button does.
 *  - The price was never shown anywhere before the redirect. It is now.
 */
function LimitModal({ detail, onClose }) {
  const { t } = useTranslation();
  const { startUpgrade, loading } = useUpgrade();
  if (!detail) return null;

  const isDaily = detail.code === "daily_pages_exceeded";
  const isPro = isPaidPlan(detail.plan);
  const planName = isPro ? t("plans.pro") : t("plans.free");
  const body = isDaily
    ? t("limits.daily", { used: detail.used, limit: detail.limit, plan: planName })
    : t("limits.doc", { used: detail.used, limit: detail.limit, plan: planName });

  return (
    <Modal isOpen onClose={onClose} title={t("limits.title")}>
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 shrink-0 border border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 flex items-center justify-center">
          <Gauge className="w-4 h-4 text-amber-600 dark:text-amber-400" />
        </div>
        <div className="space-y-2">
          <p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">{body}</p>
          <p className="text-xs text-zinc-400 dark:text-zinc-500">
            {isPro ? t("usage.resets") : t("limits.upgradeHint")}
          </p>
        </div>
      </div>

      {/* The price, before anyone is sent to a card form. */}
      {!isPro && (
        <div className="mt-5 border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 px-4 py-3">
          <p className="text-sm font-medium text-zinc-800 dark:text-zinc-100">
            {t("limits.proPrice")}
          </p>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5">
            <ExternalLink className="w-3 h-3 shrink-0" />
            {t("limits.checkoutNote")}
          </p>
        </div>
      )}

      <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
        <button onClick={onClose} className="btn-secondary justify-center px-4 py-2 text-sm">
          {t("limits.close")}
        </button>
        {!isPro && (
          <button
            onClick={startUpgrade}
            disabled={loading}
            className="btn-primary justify-center px-4 py-2 text-sm"
          >
            {loading ? t("billing.redirecting") : t("limits.upgradeCta")}
          </button>
        )}
      </div>
    </Modal>
  );
}

export default LimitModal;

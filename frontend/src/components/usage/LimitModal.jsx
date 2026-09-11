import React from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Gauge } from "lucide-react";
import Modal from "../ui/Modal";
import { UPGRADE_PATH, PLAN_PRO } from "../../constants/plans";

/**
 * Shown when the API answers 402 with a plan-quota detail
 * ({code, message, limit, used, plan}). Mounted once in Routes and driven by
 * the onQuotaExceeded event from the API client.
 */
function LimitModal({ detail, onClose }) {
  const { t } = useTranslation();
  if (!detail) return null;

  const isDaily = detail.code === "daily_pages_exceeded";
  const isPro = detail.plan === PLAN_PRO;
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
      <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
        <button onClick={onClose} className="btn-secondary justify-center px-4 py-2 text-sm">
          {t("limits.close")}
        </button>
        {!isPro && (
          <Link to={UPGRADE_PATH} onClick={onClose} className="btn-primary justify-center px-4 py-2 text-sm">
            {t("limits.upgradeCta")}
          </Link>
        )}
      </div>
    </Modal>
  );
}

export default LimitModal;

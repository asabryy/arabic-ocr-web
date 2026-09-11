import React from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { UPGRADE_PATH, PLAN_PRO } from "../../constants/plans";

/**
 * "N / M pages today" bar. Pass the object from useUsage(); renders a skeleton
 * while loading and nothing if usage is unavailable.
 */
function UsageMeter({ usage, loading, compact = false }) {
  const { t } = useTranslation();

  if (loading) return <div className={`skel h-4 ${compact ? "w-32" : "w-44"}`} />;
  if (!usage) return null;

  const { used_today: used, daily_limit: limit, plan } = usage;
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const nearLimit = pct >= 80;
  const atLimit = used >= limit;

  return (
    <div className={compact ? "min-w-[9rem]" : "min-w-[12rem]"}>
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <span className="text-xs text-zinc-500 dark:text-zinc-400 tabular-nums">
          {t("usage.today", { used, limit })}
        </span>
        {plan !== PLAN_PRO && atLimit && (
          <Link to={UPGRADE_PATH} className="text-xs font-medium text-indigo-500 hover:text-indigo-600">
            {t("plans.upgrade")}
          </Link>
        )}
      </div>
      <div className="h-1.5 w-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden" aria-hidden>
        <div
          className={`h-full transition-all duration-500 ${atLimit ? "bg-red-500" : nearLimit ? "bg-amber-500" : "bg-indigo-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {!compact && (
        <p className="text-[11px] text-zinc-400 dark:text-zinc-600 mt-1">
          {t("usage.perDoc", { limit: usage.max_doc_pages })} · {t("usage.resets")}
        </p>
      )}
    </div>
  );
}

export default UsageMeter;

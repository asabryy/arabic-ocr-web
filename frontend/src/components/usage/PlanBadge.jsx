import React from "react";
import { useTranslation } from "react-i18next";
import { PLAN_UNLIMITED, isPaidPlan } from "../../constants/plans";

/** Small pill showing the account tier. */
function PlanBadge({ plan }) {
  const { t } = useTranslation();
  const isPro = isPaidPlan(plan);
  const isUnlimited = plan === PLAN_UNLIMITED;
  return (
    <span
      className={[
        "inline-flex items-center px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider border",
        isPro
          ? "border-indigo-300 dark:border-indigo-600 text-indigo-600 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-500/10"
          : "border-zinc-200 dark:border-zinc-700 text-zinc-500 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-800/60",
      ].join(" ")}
    >
      {isPro ? t("plans.pro") : t("plans.free")}
    </span>
  );
}

export default PlanBadge;

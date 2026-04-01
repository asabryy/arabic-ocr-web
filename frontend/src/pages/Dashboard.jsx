import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { fetchDocuments } from "../api/docs";
import { FileText, ArrowRight } from "lucide-react";

function StatusText({ status }) {
  const { t } = useTranslation();
  const cls = {
    pending:    "status-pending",
    processing: "status-processing",
    done:       "status-done",
    failed:     "status-failed",
  }[status] ?? "status-pending";
  return <span className={cls}>{t(`convert.status.${status}`, { defaultValue: status })}</span>;
}

function Dashboard() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [docs, setDocs] = useState(null);

  useEffect(() => {
    fetchDocuments()
      .then((data) => setDocs(Array.isArray(data) ? data : []))
      .catch(() => setDocs([]));
  }, []);

  const loading    = docs === null;
  const total      = docs?.length ?? 0;
  const converting = docs?.filter((d) => d.status === "processing" || d.status === "pending").length ?? 0;
  const converted  = docs?.filter((d) => d.status === "done").length ?? 0;
  const failed     = docs?.filter((d) => d.status === "failed").length ?? 0;
  const recent     = docs ? [...docs].sort((a, b) => b.last_modified - a.last_modified).slice(0, 5) : [];
  const firstName  = user?.name?.split(" ")[0];

  return (
    <div className="space-y-8 animate-fade-in">

      {/* Page header */}
      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-5">
        <h1 className="text-xl font-semibold tracking-tight">
          {firstName ? t("dashboard.welcomeBack", { name: firstName }) : t("dashboard.title")}
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">{t("dashboard.subtitle")}</p>
      </div>

      {/* ── Stats: inline bar with dividers, not cards ── */}
      <div>
        <p className="section-label mb-4">{t("dashboard.overview") ?? "Overview"}</p>
        {loading ? (
          <div className="grid grid-cols-4 divide-x divide-zinc-200 dark:divide-zinc-800 border border-zinc-200 dark:border-zinc-800">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="px-5 py-5 space-y-2">
                <div className="skel h-7 w-10" />
                <div className="skel h-3 w-16" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-y sm:divide-y-0 divide-zinc-200 dark:divide-zinc-800 border border-zinc-200 dark:border-zinc-800">
            {[
              { value: total,      label: t("dashboard.stats.total"),      cls: "text-zinc-900 dark:text-zinc-100" },
              { value: converting, label: t("dashboard.stats.converting"), cls: "text-indigo-500 dark:text-indigo-400" },
              { value: converted,  label: t("dashboard.stats.converted"),  cls: "text-emerald-600 dark:text-emerald-400" },
              { value: failed,     label: t("dashboard.stats.failed"),     cls: "text-red-500 dark:text-red-400" },
            ].map(({ value, label, cls }) => (
              <div key={label} className="px-5 py-5">
                <p className={`text-3xl font-bold tabular-nums ${cls}`}>{value}</p>
                <p className="section-label mt-1.5">{label}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Recent conversions: table layout ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <p className="section-label">{t("dashboard.recentConversions")}</p>
          <Link to="/convert"
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-500 dark:text-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-300 transition-colors"
          >
            {t("dashboard.goToConvert")}
            <ArrowRight className="w-3 h-3 rtl:rotate-180" />
          </Link>
        </div>

        <div className="border border-zinc-200 dark:border-zinc-800">
          {/* Table header */}
          <div className="grid grid-cols-[1fr_auto_auto] gap-4 px-4 py-2 bg-zinc-50 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
            <span className="section-label">File name</span>
            <span className="section-label">Status</span>
            <span className="section-label">Date</span>
          </div>

          {loading && (
            <>
              {[...Array(3)].map((_, i) => (
                <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-4 items-center px-4 py-3.5 border-b border-zinc-100 dark:border-zinc-800 last:border-0">
                  <div className="flex items-center gap-2.5">
                    <div className="skel w-4 h-4 shrink-0" />
                    <div className="skel h-3 w-48" />
                  </div>
                  <div className="skel h-3 w-14" />
                  <div className="skel h-3 w-20" />
                </div>
              ))}
            </>
          )}

          {!loading && recent.length === 0 && (
            <div className="px-4 py-14 flex flex-col items-center text-center">
              <FileText className="w-8 h-8 text-zinc-300 dark:text-zinc-700 mb-3" />
              <p className="text-sm font-medium mb-1">{t("dashboard.empty.title")}</p>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xs leading-relaxed mb-5">
                {t("dashboard.empty.body")}
              </p>
              <Link to="/convert" className="btn-primary text-xs px-4 py-1.5">
                {t("dashboard.empty.cta")}
              </Link>
            </div>
          )}

          {!loading && recent.length > 0 && (
            <>
              {recent.map((doc) => (
                <div key={doc.filename}
                  className="grid grid-cols-[1fr_auto_auto] gap-4 items-center px-4 py-3.5 border-b border-zinc-100 dark:border-zinc-800 last:border-0 hover:bg-zinc-50/60 dark:hover:bg-zinc-900/40 transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <FileText className="w-3.5 h-3.5 text-zinc-300 dark:text-zinc-600 shrink-0" />
                    <p className="text-sm truncate">{doc.filename}</p>
                  </div>
                  <StatusText status={doc.status} />
                  <p className="text-xs text-zinc-400 dark:text-zinc-500 whitespace-nowrap">
                    {new Date(doc.last_modified * 1000).toLocaleDateString()}
                  </p>
                </div>
              ))}
              {total > 5 && (
                <div className="px-4 py-2.5 bg-zinc-50 dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800">
                  <Link to="/convert" className="text-xs text-indigo-500 dark:text-indigo-400 hover:underline">
                    {t("dashboard.viewAll", { count: total })}
                  </Link>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;

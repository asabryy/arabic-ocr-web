import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { fetchDocuments } from "../api/docs";
import { FileText, Loader2, CircleCheck, XCircle, ChevronRight } from "lucide-react";

function StatCard({ icon: Icon, label, value, colorClass }) {
  return (
    <div className="glass-card rounded-2xl p-5 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${colorClass}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
        <p className="text-2xl font-bold tabular-nums">{value}</p>
      </div>
    </div>
  );
}

function StatSkeleton() {
  return (
    <div className="glass-card rounded-2xl p-5 flex items-center gap-4">
      <div className="w-10 h-10 rounded-xl bg-zinc-100 dark:bg-zinc-800 animate-pulse shrink-0" />
      <div className="space-y-2 flex-1">
        <div className="h-3 w-20 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
        <div className="h-6 w-10 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
      </div>
    </div>
  );
}

function RecentRow({ doc }) {
  const STATUS = {
    pending: "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400",
    processing: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
    done: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    failed: "bg-red-500/10 text-red-600 dark:text-red-400",
  };
  return (
    <li className="flex items-center gap-3 py-3 border-b border-zinc-100 dark:border-zinc-800 last:border-0">
      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 flex items-center justify-center shrink-0">
        <FileText className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{doc.filename}</p>
        <p className="text-xs text-zinc-400 dark:text-zinc-500">
          {new Date(doc.last_modified * 1000).toLocaleDateString()}
        </p>
      </div>
      <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${STATUS[doc.status] ?? STATUS.pending}`}>
        {doc.status}
      </span>
    </li>
  );
}

function RecentRowSkeleton() {
  return (
    <li className="flex items-center gap-3 py-3 border-b border-zinc-100 dark:border-zinc-800 last:border-0">
      <div className="w-8 h-8 rounded-xl bg-zinc-100 dark:bg-zinc-800 animate-pulse shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3.5 w-48 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
        <div className="h-2.5 w-24 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
      </div>
      <div className="h-5 w-14 bg-zinc-100 dark:bg-zinc-800 rounded-full animate-pulse" />
    </li>
  );
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

  const loading = docs === null;
  const total = docs?.length ?? 0;
  const converting = docs?.filter((d) => d.status === "processing" || d.status === "pending").length ?? 0;
  const converted = docs?.filter((d) => d.status === "done").length ?? 0;
  const failed = docs?.filter((d) => d.status === "failed").length ?? 0;
  const recent = docs ? [...docs].sort((a, b) => b.last_modified - a.last_modified).slice(0, 5) : [];
  const firstName = user?.name?.split(" ")[0];

  return (
    <div className="space-y-7">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {firstName ? t("dashboard.welcomeBack", { name: firstName }) : t("dashboard.title")}
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">{t("dashboard.subtitle")}</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {loading ? (
          <>
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
          </>
        ) : (
          <>
            <StatCard icon={FileText} label={t("dashboard.stats.total")} value={total} colorClass="bg-indigo-500/10 text-indigo-500 dark:text-indigo-400" />
            <StatCard icon={Loader2} label={t("dashboard.stats.converting")} value={converting} colorClass="bg-amber-500/10 text-amber-500 dark:text-amber-400" />
            <StatCard icon={CircleCheck} label={t("dashboard.stats.converted")} value={converted} colorClass="bg-emerald-500/10 text-emerald-500 dark:text-emerald-400" />
            <StatCard icon={XCircle} label={t("dashboard.stats.failed")} value={failed} colorClass="bg-red-500/10 text-red-500 dark:text-red-400" />
          </>
        )}
      </div>

      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold">{t("dashboard.recentConversions")}</h2>
          <Link
            to="/convert"
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-500 dark:text-indigo-400 hover:underline"
          >
            {t("dashboard.goToConvert")}
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loading && (
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            <RecentRowSkeleton />
            <RecentRowSkeleton />
            <RecentRowSkeleton />
          </ul>
        )}

        {!loading && recent.length === 0 && (
          <div className="py-10 flex flex-col items-center text-center">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-4">
              <FileText className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />
            </div>
            <p className="text-sm font-medium mb-1">{t("dashboard.empty.title")}</p>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xs leading-relaxed mb-4">
              {t("dashboard.empty.body")}
            </p>
            <Link
              to="/convert"
              className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white transition-colors"
            >
              {t("dashboard.empty.cta")}
            </Link>
          </div>
        )}

        {!loading && recent.length > 0 && (
          <>
            <ul>
              {recent.map((doc) => (
                <RecentRow key={doc.filename} doc={doc} />
              ))}
            </ul>
            {total > 5 && (
              <div className="mt-4 text-center">
                <Link
                  to="/convert"
                  className="text-xs text-indigo-500 dark:text-indigo-400 hover:underline"
                >
                  {t("dashboard.viewAll", { count: total })}
                </Link>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default Dashboard;

import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Loader2, Download, FileText, CheckCircle2, AlertTriangle, RotateCcw, ArrowRight } from "lucide-react";
import Dropzone from "../upload/Dropzone";
import { uploadTrial, fetchTrialStatus, downloadTrialDocx } from "../../api/docs";

const POLL_MS = 3000;
const TIMEOUT_MS = 3 * 60 * 1000;
const TRIAL_MAX_MB = 10;

/**
 * Landing-page "try one page free" widget. No account needed.
 *
 * idle → uploading → processing → done
 *          ├ 429 → limited          (daily trial budget for this IP is spent)
 *          ├ 400 → idle + toast     (not a readable PDF)
 *          └ other / "failed" / timeout → failed
 *
 * The closing pitch used to read "247 more pages in this document" directly above
 * "Sign up free to convert the whole document" — a promise no plan keeps in one
 * go, made at the exact moment an email address changes hands. It now states what
 * a free account really does (batches of `free_max_doc_pages`, resuming where it
 * stopped) using the limits the API reports, not numbers typed into a locale file.
 */
function TrialBox({ openRegister }) {
  const { t } = useTranslation();
  const [phase, setPhase] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [trial, setTrial] = useState(null); // {trial_id, pages_total, max_pages}
  const [fileName, setFileName] = useState("");
  const pollRef = useRef(null);
  const startedAt = useRef(0);

  const stopPolling = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  useEffect(() => stopPolling, []);

  useEffect(() => {
    if (phase !== "processing" || !trial) return undefined;
    startedAt.current = Date.now();
    pollRef.current = setInterval(async () => {
      if (Date.now() - startedAt.current > TIMEOUT_MS) { stopPolling(); setPhase("failed"); return; }
      try {
        const s = await fetchTrialStatus(trial.trial_id);
        if (s.status === "done") { stopPolling(); setPhase("done"); }
        else if (s.status === "failed") { stopPolling(); setPhase("failed"); }
      } catch { /* transient; keep polling until timeout */ }
    }, POLL_MS);
    return stopPolling;
  }, [phase, trial]);

  const reset = () => { stopPolling(); setPhase("idle"); setTrial(null); setProgress(0); setFileName(""); };

  const handleFile = async (file) => {
    setFileName(file.name);
    setPhase("uploading");
    setProgress(0);
    try {
      const res = await uploadTrial(file, setProgress);
      setTrial(res);
      setPhase("processing");
    } catch (err) {
      const status = err?.response?.status;
      if (status === 429) { setPhase("limited"); return; }
      if (status === 400) { toast.error(t("trial.invalidPdf")); setPhase("idle"); return; }
      if (status === 413) { toast.error(t("trial.tooLarge", { mb: TRIAL_MAX_MB })); setPhase("idle"); return; }
      setPhase("failed");
    }
  };

  const handleDownload = async () => {
    try {
      const stem = fileName.replace(/\.[^.]+$/, "") || "document";
      await downloadTrialDocx(trial.trial_id, `${stem}.docx`);
    } catch { toast.error(t("trial.failed")); }
  };

  const remaining = trial ? Math.max(0, trial.pages_total - trial.max_pages) : 0;
  // Served by the trial API so the copy tracks the deployed plan limits.
  const freePerDoc = trial?.free_max_doc_pages ?? 10;
  const freeDaily = trial?.free_daily_pages ?? 10;
  const proPerDoc = trial?.pro_max_doc_pages ?? 40;
  const proDaily = trial?.pro_daily_pages ?? 50;
  // Only worth naming Pro when the free batch size is genuinely the slow way round.
  const proWorthMentioning = remaining > freePerDoc;

  return (
    <div className="w-full">
      <div className="h-0.5 w-full bg-indigo-500" />
      <div className="studio-card overflow-hidden shadow-xl shadow-zinc-200/60 dark:shadow-black/40">
        {/* Header */}
        <div className="flex items-center justify-between gap-3 px-5 py-3 border-b border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
          <div>
            <p className="text-sm font-semibold">{t("trial.title")}</p>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">{t("trial.subtitle")}</p>
          </div>
          <span className="section-label text-indigo-500 shrink-0">{t("trial.freeTag")}</span>
        </div>

        <div className="p-5">
          {phase === "idle" && (
            <Dropzone
              onFile={handleFile}
              compact
              showShortcutHint={false}
              maxSizeMb={TRIAL_MAX_MB}
              subtitle={t("trial.dropSubtitle", { mb: TRIAL_MAX_MB })}
            />
          )}

          {phase === "uploading" && (
            <div className="py-8 space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
                <span className="truncate">{t("trial.uploading", { name: fileName })}</span>
              </div>
              <div className="h-1.5 w-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
                <div className="h-full bg-indigo-500 transition-all" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {phase === "processing" && (
            <div className="py-8 flex flex-col items-center text-center gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
              <p className="text-sm font-medium">{t("trial.processing")}</p>
              {trial && (
                <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xs">
                  {t("trial.onlyFirstPage", { total: trial.pages_total })}
                </p>
              )}
            </div>
          )}

          {phase === "done" && (
            <div className="py-4 space-y-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium">{t("trial.done")}</p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5 mt-0.5">
                    <FileText className="w-3 h-3" /> <span className="truncate max-w-[14rem]">{fileName}</span>
                  </p>
                </div>
              </div>
              <button onClick={handleDownload} className="btn-primary w-full justify-center gap-2 py-2.5 text-sm">
                <Download className="w-4 h-4" /> {t("trial.download")}
              </button>
              <div className="border-t border-zinc-100 dark:border-zinc-800 pt-4">
                <div className="text-xs text-zinc-500 dark:text-zinc-400 mb-2 space-y-1">
                  {remaining > 0 ? (
                    <>
                      <p className="text-zinc-600 dark:text-zinc-300">
                        {t("trial.remainingPages", { count: remaining })}
                      </p>
                      <p>{t("trial.afterTrial.free", { perDoc: freePerDoc })}</p>
                      {proWorthMentioning && (
                        <p>{t("trial.afterTrial.pro", { perDoc: proPerDoc, daily: proDaily })}</p>
                      )}
                    </>
                  ) : (
                    <p>{t("trial.moreDocs", { daily: freeDaily })}</p>
                  )}
                </div>
                <button onClick={openRegister} className="btn-secondary w-full justify-center gap-2 py-2 text-sm group">
                  {t("trial.signupCta")}
                  <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 rtl:rotate-180" />
                </button>
                <button onClick={reset} className="mt-2 w-full text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors">
                  {t("trial.tryAnother")}
                </button>
              </div>
            </div>
          )}

          {phase === "limited" && (
            <div className="py-6 space-y-4 text-center">
              <AlertTriangle className="w-6 h-6 text-amber-500 mx-auto" />
              <div>
                <p className="text-sm font-medium">{t("trial.limited.title")}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-xs mx-auto">{t("trial.limited.body")}</p>
              </div>
              <button onClick={openRegister} className="btn-primary w-full justify-center gap-2 py-2.5 text-sm group">
                {t("trial.signupCta")}
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 rtl:rotate-180" />
              </button>
            </div>
          )}

          {phase === "failed" && (
            <div className="py-6 space-y-4 text-center">
              <AlertTriangle className="w-6 h-6 text-red-500 mx-auto" />
              <p className="text-sm text-zinc-600 dark:text-zinc-300">{t("trial.failed")}</p>
              <button onClick={reset} className="btn-secondary justify-center gap-2 py-2 text-sm">
                <RotateCcw className="w-3.5 h-3.5" /> {t("trial.retry")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TrialBox;

import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { updateCurrentUser, resendVerificationEmail } from "../features/auth/authservice";
import { createPortalSession } from "../api/billing";
import { PLAN_PRO, PLAN_UNLIMITED, isPaidPlan } from "../constants/plans";
import { useUpgrade } from "../hooks/useUpgrade";

function SettingsPage() {
  const { t } = useTranslation();
  const { user, login } = useAuth();
  const { startUpgrade, loading: upgrading, error: upgradeError } = useUpgrade();
  const [portalLoading, setPortalLoading] = useState(false);
  const [portalError, setPortalError] = useState(false);
  const [name, setName] = useState(user?.name || "");
  const [email] = useState(user?.email || "");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    setStatus("");
    const token = localStorage.getItem("access_token");
    try {
      await updateCurrentUser(token, { name });
      await login(token);
      setStatus("saved");
    } catch {
      setStatus("error");
    } finally {
      setLoading(false);
    }
  };

  const [resendState, setResendState] = useState("idle"); // idle|sending|sent|limited|error

  const resendVerification = async () => {
    setResendState("sending");
    try {
      await resendVerificationEmail();
      setResendState("sent");
    } catch (err) {
      // 429 is the server's 1-per-5-minutes guard, which is worth saying plainly
      // rather than reporting as a generic failure.
      setResendState(err?.response?.status === 429 ? "limited" : "error");
    }
  };

  // Card changes, invoices and cancellation all live in Stripe's portal — there is
  // deliberately no in-app subscription management UI to keep in sync.
  const openPortal = async () => {
    setPortalLoading(true);
    setPortalError(false);
    try {
      window.location.assign(await createPortalSession());
    } catch {
      setPortalError(true);
      setPortalLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-lg">
      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-5">
        <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">Manage your account</p>
      </div>

      <div className="border border-zinc-200 dark:border-zinc-800 border-t-2 border-t-indigo-500">
        <div className="px-5 py-4 border-b border-zinc-100 dark:border-zinc-800">
          <p className="section-label">Profile</p>
        </div>
        <div className="px-5 py-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
              Name
            </label>
            <input type="text" className="field-input" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
              Email
            </label>
            <input type="email" value={email} className="field-input opacity-50 cursor-not-allowed" disabled />
          </div>

          {/* The API field is email_verified; this used to read user.is_verified,
              which is always undefined — so the warning showed to everyone. */}
          {!user?.email_verified && (
            <div className="flex items-start gap-2 px-3 py-2.5 bg-amber-50 dark:bg-amber-500/5 border border-amber-200 dark:border-amber-500/20 text-sm">
              <span className="text-amber-500 mt-0.5">⚠</span>
              <span className="text-amber-700 dark:text-amber-400">
                {t("verify.notVerified")}{" "}
                {resendState === "sent" ? (
                  <span className="text-emerald-600 dark:text-emerald-400">{t("verify.sent")}</span>
                ) : (
                  <button
                    onClick={resendVerification}
                    disabled={resendState === "sending"}
                    className="underline text-indigo-500 hover:text-indigo-600 disabled:opacity-60"
                  >
                    {resendState === "sending" ? t("verify.sending") : t("verify.resend")}
                  </button>
                )}
                {resendState === "limited" && (
                  <span className="block text-xs text-amber-600 dark:text-amber-500 mt-1">
                    {t("verify.limited")}
                  </span>
                )}
                {resendState === "error" && (
                  <span className="block text-xs text-red-500 mt-1">{t("verify.error")}</span>
                )}
              </span>
            </div>
          )}

          <div className="flex items-center gap-3 pt-1">
            <button onClick={handleSave} disabled={loading} className="btn-primary px-5 py-2">
              {loading ? "Saving…" : "Save Changes"}
            </button>
            {status === "saved" && <p className="text-xs text-emerald-600 dark:text-emerald-400">Saved successfully.</p>}
            {status === "error" && <p className="text-xs text-red-500">Failed to update. Please try again.</p>}
          </div>
        </div>
      </div>

      <div className="border border-zinc-200 dark:border-zinc-800 border-t-2 border-t-indigo-500">
        <div className="px-5 py-4 border-b border-zinc-100 dark:border-zinc-800">
          <p className="section-label">{t("billing.section")}</p>
        </div>
        <div className="px-5 py-5 space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-zinc-700 dark:text-zinc-300">
                {t("billing.currentPlan")}{" "}
                <span className="font-semibold">
                  {t(`plans.${user?.plan === PLAN_UNLIMITED ? "unlimited" : user?.plan === PLAN_PRO ? "pro" : "free"}`)}
                </span>
              </p>
              <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5">
                {isPaidPlan(user?.plan) ? t("billing.manageHint") : t("billing.upgradeHint")}
              </p>
            </div>
            {isPaidPlan(user?.plan) ? (
              <button onClick={openPortal} disabled={portalLoading} className="btn-secondary px-4 py-2 shrink-0">
                {portalLoading ? t("billing.redirecting") : t("billing.manage")}
              </button>
            ) : (
              <button onClick={startUpgrade} disabled={upgrading} className="btn-primary px-4 py-2 shrink-0">
                {upgrading ? t("billing.redirecting") : t("pricing.cta.upgrade")}
              </button>
            )}
          </div>
          {portalError && <p className="text-xs text-red-500">{t("billing.errors.failed")}</p>}
          {upgradeError && (
            <p className="text-xs text-red-500">
              {t(upgradeError === "already_pro" ? "billing.errors.alreadyPro" : "billing.errors.failed")}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;

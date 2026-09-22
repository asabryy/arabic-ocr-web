import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { MessageSquare } from "lucide-react";
import Modal from "../ui/Modal";
import { useAuth } from "../../auth/AuthContext";
import { onFeedbackRequested, sendFeedback } from "../../api/feedback";

const CATEGORIES = ["bug", "feedback", "support"];
const MAX = 4000;

/**
 * Mounted once in Routes and opened via openFeedback() from anywhere.
 * Anonymous users get an email field; signed-in users don't, because the server
 * uses their account address regardless of what the form says.
 */
function FeedbackModal() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState("bug");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [website, setWebsite] = useState(""); // honeypot
  const [state, setState] = useState("idle"); // idle | sending | sent | error
  const [page, setPage] = useState("");

  useEffect(
    () =>
      onFeedbackRequested((ctx = {}) => {
        setCategory(ctx.category || "bug");
        setPage(ctx.page || window.location.pathname);
        setState("idle");
        setMessage("");
        setOpen(true);
      }),
    []
  );

  const close = () => setOpen(false);

  const submit = async (e) => {
    e.preventDefault();
    setState("sending");
    try {
      await sendFeedback({ category, message, email, page, website });
      setState("sent");
    } catch {
      setState("error");
    }
  };

  if (!open) return null;

  const tooShort = message.trim().length < 10;

  return (
    <Modal isOpen onClose={close} title={t("feedback.title")}>
      {state === "sent" ? (
        <div className="space-y-4">
          <p className="text-sm text-zinc-700 dark:text-zinc-300">{t("feedback.sent")}</p>
          <div className="flex justify-end">
            <button onClick={close} className="btn-primary px-4 py-2 text-sm">
              {t("feedback.close")}
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 shrink-0 border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            </div>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
              {t("feedback.intro")}
            </p>
          </div>

          <div className="flex gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCategory(c)}
                className={
                  category === c
                    ? "btn-primary px-3 py-1.5 text-xs"
                    : "btn-secondary px-3 py-1.5 text-xs"
                }
              >
                {t(`feedback.categories.${c}`)}
              </button>
            ))}
          </div>

          {!user && (
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
                {t("feedback.email")}
              </label>
              <input
                type="email"
                required
                className="field-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
              {t("feedback.message")}
            </label>
            <textarea
              required
              rows={5}
              maxLength={MAX}
              className="field-input resize-none"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={t("feedback.placeholder")}
            />
            <p className="text-[11px] text-zinc-400 mt-1 tabular-nums">
              {message.length} / {MAX}
            </p>
          </div>

          {/* Honeypot — hidden from people, tempting to bots. */}
          <input
            type="text"
            name="website"
            tabIndex={-1}
            autoComplete="off"
            aria-hidden="true"
            className="hidden"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
          />

          {state === "error" && <p className="text-xs text-red-500">{t("feedback.error")}</p>}

          <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 pt-1">
            <button type="button" onClick={close} className="btn-secondary justify-center px-4 py-2 text-sm">
              {t("feedback.cancel")}
            </button>
            <button
              type="submit"
              disabled={state === "sending" || tooShort}
              className="btn-primary justify-center px-4 py-2 text-sm"
            >
              {state === "sending" ? t("feedback.sending") : t("feedback.submit")}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}

export default FeedbackModal;

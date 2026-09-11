import React, { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Upload } from "lucide-react";

/**
 * PDF drop target. Extracted from ConvertPage so the landing-page trial can reuse it.
 *
 * Props:
 *  - onFile(file)        called with a validated PDF
 *  - disabled            greys out and ignores input
 *  - maxSizeMb           client-side size guard (default 50)
 *  - compact             tighter padding for embedding in a card
 *  - showShortcutHint    show the "Press U to browse" hint (ConvertPage only)
 *  - subtitle            override the secondary line
 */
function Dropzone({
  onFile,
  disabled,
  maxSizeMb = 50,
  compact = false,
  showShortcutHint = true,
  subtitle,
}) {
  const { t } = useTranslation();
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleFile = (file) => {
    if (!file) return;
    if (file.type !== "application/pdf") { toast.error(t("convert.onlyPdf")); return; }
    if (file.size > maxSizeMb * 1024 * 1024) { toast.error(t("convert.tooLarge")); return; }
    onFile(file);
  };

  return (
    <div
      onClick={() => !disabled && inputRef.current?.click()}
      onDrop={(e) => { e.preventDefault(); setDragging(false); if (!disabled) handleFile(e.dataTransfer.files?.[0]); }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      className={[
        "border-2 border-dashed flex flex-col items-center gap-3 select-none transition-all duration-150",
        compact ? "py-7" : "py-10",
        disabled
          ? "opacity-40 cursor-not-allowed border-zinc-200 dark:border-zinc-800"
          : dragging
          ? "border-indigo-400 bg-indigo-50/40 dark:bg-indigo-500/5 cursor-copy"
          : "border-zinc-200 dark:border-zinc-700 hover:border-indigo-300 dark:hover:border-indigo-700 hover:bg-zinc-50/40 dark:hover:bg-zinc-900/40 cursor-pointer",
      ].join(" ")}
    >
      <input ref={inputRef} type="file" accept="application/pdf" className="hidden"
        onChange={(e) => { handleFile(e.target.files?.[0]); e.target.value = ""; }} />
      <div className={[
        "w-10 h-10 flex items-center justify-center transition-colors border",
        dragging
          ? "border-indigo-300 text-indigo-500 bg-indigo-50 dark:bg-indigo-500/10"
          : "border-zinc-200 dark:border-zinc-700 text-zinc-400",
      ].join(" ")}>
        <Upload className="w-4 h-4" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium">{t("convert.dropzone.title")}</p>
        <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5">
          {subtitle ?? t("convert.dropzone.subtitle")}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <button type="button" disabled={disabled} className="btn-secondary text-xs px-3 py-1.5 gap-1.5">
          <Upload className="w-3 h-3" />
          {t("convert.dropzone.browse")}
        </button>
        {showShortcutHint && (
          <span className="text-xs text-zinc-300 dark:text-zinc-700 select-none">
            {t("convert.dropzone.shortcutPrefix")}{" "}
            <kbd className="px-1 py-0.5 text-[10px] border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 font-mono">U</kbd>{" "}
            {t("convert.dropzone.shortcutSuffix")}
          </span>
        )}
      </div>
    </div>
  );
}

export default Dropzone;

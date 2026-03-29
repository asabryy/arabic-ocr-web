import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import toast from "react-hot-toast";
import { FileText, Upload, Loader2, Zap, Trash2, Download } from "lucide-react";
import {
  fetchDocuments,
  uploadDocument,
  deleteDocument,
  convertDocument,
  getPreviewBlob,
  downloadDocument,
} from "../api/docs";
import PDFViewer from "../components/pdf/PDFViewer";

const STATUS_STYLES = {
  pending: "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400",
  processing: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
  done: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  failed: "bg-red-500/10 text-red-600 dark:text-red-400",
};

function StatusBadge({ status }) {
  const { t } = useTranslation();
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full ${style}`}>
      {status === "processing" && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
      {t(`convert.status.${status}`, { defaultValue: status })}
    </span>
  );
}

function UploadProgress({ filename, progress }) {
  return (
    <div className="rounded-xl border border-indigo-200 dark:border-indigo-500/20 bg-indigo-50 dark:bg-indigo-500/5 p-4 space-y-2">
      <div className="flex justify-between items-center text-sm">
        <span className="font-medium truncate max-w-xs text-indigo-700 dark:text-indigo-300">{filename}</span>
        <span className="text-indigo-400 ml-4 shrink-0 tabular-nums">{progress}%</span>
      </div>
      <div className="h-1.5 bg-indigo-100 dark:bg-indigo-500/20 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all duration-150"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

function SkeletonRow() {
  return (
    <div className="p-3 border border-zinc-100 dark:border-zinc-800 rounded-xl flex items-center justify-between gap-3">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="w-8 h-8 rounded-xl bg-zinc-100 dark:bg-zinc-800 animate-pulse shrink-0" />
        <div className="flex-1 space-y-1.5">
          <div className="h-3.5 w-48 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
          <div className="h-2.5 w-24 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="h-5 w-16 bg-zinc-100 dark:bg-zinc-800 rounded-full animate-pulse" />
        <div className="h-7 w-20 bg-zinc-100 dark:bg-zinc-800 rounded-lg animate-pulse" />
      </div>
    </div>
  );
}

function Dropzone({ onFile, disabled }) {
  const { t } = useTranslation();
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleFile = (file) => {
    if (!file) return;
    if (file.type !== "application/pdf") {
      toast.error(t("convert.onlyPdf"));
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      toast.error(t("convert.tooLarge"));
      return;
    }
    onFile(file);
  };

  return (
    <div
      onClick={() => !disabled && inputRef.current?.click()}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFile(e.dataTransfer.files?.[0]);
      }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      className={[
        "border-2 border-dashed rounded-2xl px-6 py-10 flex flex-col items-center gap-3 transition-all duration-150 select-none",
        disabled
          ? "opacity-50 cursor-not-allowed border-zinc-200 dark:border-zinc-800"
          : dragging
          ? "border-indigo-400 bg-indigo-50/60 dark:bg-indigo-500/10 cursor-copy"
          : "border-zinc-200 dark:border-zinc-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-zinc-50/60 dark:hover:bg-zinc-800/40 cursor-pointer",
      ].join(" ")}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <div
        className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-colors ${
          dragging ? "bg-indigo-500/15 text-indigo-500" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-400"
        }`}
      >
        <Upload className="w-6 h-6" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{t("convert.dropzone.title")}</p>
        <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">{t("convert.dropzone.subtitle")}</p>
      </div>
      <button
        type="button"
        disabled={disabled}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 border border-zinc-200 dark:border-zinc-700 transition-colors disabled:opacity-50 disabled:pointer-events-none"
      >
        <Upload className="w-3.5 h-3.5" />
        {t("convert.dropzone.browse")}
      </button>
    </div>
  );
}

function ConvertPage() {
  const { t } = useTranslation();
  const { user, loading: authLoading } = useAuth();
  const [docs, setDocs] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [converting, setConverting] = useState(new Set());
  const pollRef = useRef(null);

  const loadDocs = async () => {
    try {
      const data = await fetchDocuments();
      if (Array.isArray(data)) setDocs(data);
    } catch {
      toast.error(t("convert.errors.loadFailed"));
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    if (!authLoading && user) loadDocs();
    else if (!authLoading && !user) setLoadingDocs(false);
  }, [authLoading, user]);

  // Poll while any doc is processing
  useEffect(() => {
    const hasProcessing = docs.some((d) => d.status === "processing");
    if (hasProcessing && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const data = await fetchDocuments();
          if (!Array.isArray(data)) return;
          setDocs((prev) => {
            data.forEach((d) => {
              const old = prev.find((p) => p.filename === d.filename);
              if (old?.status === "processing" && d.status === "done")
                toast.success(t("convert.toasts.done", { filename: d.filename }));
              if (old?.status === "processing" && d.status === "failed")
                toast.error(t("convert.toasts.failed", { filename: d.filename }));
            });
            return data;
          });
        } catch {}
      }, 3000);
    }
    if (!hasProcessing && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current && !hasProcessing) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [docs]);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const handleUpload = async (file) => {
    setUploadProgress({ filename: file.name, progress: 0 });
    try {
      await uploadDocument(file, (p) => setUploadProgress((prev) => ({ ...prev, progress: p })));
      toast.success(t("convert.toasts.uploaded", { filename: file.name }));
      await loadDocs();
    } catch {
      toast.error(t("convert.errors.uploadFailed"));
    } finally {
      setUploadProgress(null);
    }
  };

  const handleConvert = async (filename) => {
    setConverting((prev) => new Set(prev).add(filename));
    try {
      await convertDocument(filename);
      setDocs((prev) =>
        prev.map((d) => (d.filename === filename ? { ...d, status: "processing" } : d))
      );
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? t("convert.errors.convertFailed"));
    } finally {
      setConverting((prev) => {
        const s = new Set(prev);
        s.delete(filename);
        return s;
      });
    }
  };

  const handleSelect = async (filename) => {
    if (selectedFile === filename) {
      setSelectedFile(null);
      setPreviewUrl(null);
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(filename);
    setPreviewUrl(null);
    try {
      const url = await getPreviewBlob(filename);
      setPreviewUrl(url);
    } catch {
      toast.error(t("convert.errors.previewFailed"));
    }
  };

  const handleDelete = async (filename) => {
    try {
      await deleteDocument(filename);
      setDocs((prev) => prev.filter((d) => d.filename !== filename));
      if (selectedFile === filename) {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setSelectedFile(null);
        setPreviewUrl(null);
      }
      toast.success(t("convert.toasts.deleted"));
    } catch {
      toast.error(t("convert.errors.deleteFailed"));
    }
  };

  if (authLoading) return null;

  return (
    <div className="space-y-7">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("convert.title")}</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">{t("convert.subtitle")}</p>
      </div>

      <Dropzone onFile={handleUpload} disabled={!!uploadProgress} />

      {uploadProgress && (
        <UploadProgress filename={uploadProgress.filename} progress={uploadProgress.progress} />
      )}

      <div className="glass-card rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">{t("convert.yourFiles")}</h2>
          {!loadingDocs && docs.length > 0 && (
            <p className="text-sm text-zinc-400 dark:text-zinc-500">
              {t("convert.fileCount", { count: docs.length })}
            </p>
          )}
        </div>

        {loadingDocs && (
          <div className="space-y-2">
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </div>
        )}

        {!loadingDocs && docs.length === 0 && !uploadProgress && (
          <div className="py-12 flex flex-col items-center text-center">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-4">
              <FileText className="w-6 h-6 text-indigo-500 dark:text-indigo-400" />
            </div>
            <h3 className="text-sm font-semibold mb-1">{t("convert.empty.title")}</h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xs leading-relaxed">
              {t("convert.empty.body")}
            </p>
          </div>
        )}

        {!loadingDocs && docs.length > 0 && (
          <ul className="space-y-1.5">
            {docs.map((doc) => {
              const isConverting = converting.has(doc.filename);
              const isProcessing = doc.status === "processing";
              const busy = isConverting || isProcessing;
              return (
                <li
                  key={doc.filename}
                  onClick={() => handleSelect(doc.filename)}
                  className={[
                    "group flex items-center justify-between gap-3 p-3 rounded-xl border cursor-pointer transition-all duration-150",
                    selectedFile === doc.filename
                      ? "border-indigo-200 dark:border-indigo-500/30 bg-indigo-50/60 dark:bg-indigo-500/5"
                      : "border-zinc-100 dark:border-zinc-800 hover:border-zinc-200 dark:hover:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800/50",
                  ].join(" ")}
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div
                      className={[
                        "w-8 h-8 rounded-xl flex items-center justify-center shrink-0 transition-colors",
                        selectedFile === doc.filename
                          ? "bg-indigo-500/15 text-indigo-500"
                          : "bg-zinc-100 dark:bg-zinc-800 text-zinc-400 group-hover:text-indigo-400",
                      ].join(" ")}
                    >
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{doc.filename}</p>
                      <p className="text-xs text-zinc-400 dark:text-zinc-500">
                        {(doc.size / 1024).toFixed(1)} KB ·{" "}
                        {new Date(doc.last_modified * 1000).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div
                    className="flex items-center gap-1.5 shrink-0"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <StatusBadge status={doc.status} />
                    {doc.status === "pending" && (
                      <button
                        onClick={() => handleConvert(doc.filename)}
                        disabled={busy}
                        className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white disabled:opacity-60 transition-colors"
                      >
                        {isConverting ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Zap className="w-3.5 h-3.5" />
                        )}
                        {t("convert.actions.convert")}
                      </button>
                    )}
                    {doc.status === "failed" && (
                      <button
                        onClick={() => handleConvert(doc.filename)}
                        disabled={busy}
                        className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 disabled:opacity-60 transition-colors"
                      >
                        {isConverting ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Zap className="w-3.5 h-3.5" />
                        )}
                        {t("convert.actions.retry")}
                      </button>
                    )}
                    {doc.status === "done" && (
                      <button
                        onClick={() => downloadDocument(doc.filename.replace(/\.pdf$/, ".docx"))}
                        className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        {t("convert.actions.downloadPdf")}
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(doc.filename)}
                      className="p-1.5 rounded-lg text-zinc-300 dark:text-zinc-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {selectedFile && (
        <div className="glass-card rounded-2xl p-6 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium truncate text-zinc-700 dark:text-zinc-300">{selectedFile}</p>
            <button
              onClick={() => downloadDocument(selectedFile)}
              className="text-xs text-indigo-500 dark:text-indigo-400 hover:underline shrink-0 ltr:ml-4 rtl:mr-4 transition-colors"
            >
              {t("convert.actions.downloadPdf")}
            </button>
          </div>
          {previewUrl ? (
            <PDFViewer fileUrl={previewUrl} />
          ) : (
            <div className="p-10 flex items-center justify-center gap-2 text-sm text-zinc-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              {t("convert.previewLoading")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ConvertPage;

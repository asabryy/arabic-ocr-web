import React, { useState, useEffect, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import toast from "react-hot-toast";
import {
  FileText, Upload, Loader2, Zap, Trash2, Download, X,
  Search, ChevronUp, ChevronDown, ChevronsUpDown, CheckSquare,
} from "lucide-react";
import {
  fetchDocuments, uploadDocument, deleteDocument,
  convertDocument, getPreviewBlob, downloadDocument,
} from "../api/docs";
import PDFViewer from "../components/pdf/PDFViewer";

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtElapsed(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

const STATUS_ORDER = { processing: 0, pending: 1, failed: 2, done: 3 };

function sortDocs(docs, key, dir) {
  return [...docs].sort((a, b) => {
    let av, bv;
    if (key === "name")   { av = a.filename.toLowerCase(); bv = b.filename.toLowerCase(); }
    if (key === "status") { av = STATUS_ORDER[a.status] ?? 9; bv = STATUS_ORDER[b.status] ?? 9; }
    if (key === "date")   { av = a.last_modified; bv = b.last_modified; }
    if (av < bv) return dir === "asc" ? -1 : 1;
    if (av > bv) return dir === "asc" ?  1 : -1;
    return 0;
  });
}

// ── Sub-components ──────────────────────────────────────────────────────────

function StatusText({ status, elapsed }) {
  const { t } = useTranslation();
  const cls = {
    pending:    "status-pending",
    processing: "status-processing",
    done:       "status-done",
    failed:     "status-failed",
  }[status] ?? "status-pending";

  return (
    <span className={`inline-flex items-center gap-1 ${cls}`}>
      {status === "processing" && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
      {t(`convert.status.${status}`, { defaultValue: status })}
      {status === "processing" && elapsed != null && (
        <span className="opacity-60 font-normal normal-case tracking-normal">· {fmtElapsed(elapsed)}</span>
      )}
    </span>
  );
}

function SortHeader({ label, colKey, sortKey, sortDir, onSort }) {
  const active = sortKey === colKey;
  return (
    <button
      onClick={() => onSort(colKey)}
      className="flex items-center gap-1 section-label hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
    >
      {label}
      {active
        ? sortDir === "asc"
          ? <ChevronUp className="w-3 h-3" />
          : <ChevronDown className="w-3 h-3" />
        : <ChevronsUpDown className="w-3 h-3 opacity-40" />
      }
    </button>
  );
}

function Dropzone({ onFile, disabled }) {
  const { t } = useTranslation();
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleFile = (file) => {
    if (!file) return;
    if (file.type !== "application/pdf") { toast.error(t("convert.onlyPdf")); return; }
    if (file.size > 50 * 1024 * 1024)   { toast.error(t("convert.tooLarge")); return; }
    onFile(file);
  };

  return (
    <div
      onClick={() => !disabled && inputRef.current?.click()}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files?.[0]); }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      className={[
        "border-2 border-dashed py-10 flex flex-col items-center gap-3 select-none transition-all duration-150",
        disabled
          ? "opacity-40 cursor-not-allowed border-zinc-200 dark:border-zinc-800"
          : dragging
          ? "border-indigo-400 bg-indigo-50/40 dark:bg-indigo-500/5 cursor-copy"
          : "border-zinc-200 dark:border-zinc-700 hover:border-indigo-300 dark:hover:border-indigo-700 hover:bg-zinc-50/40 dark:hover:bg-zinc-900/40 cursor-pointer",
      ].join(" ")}
    >
      <input ref={inputRef} type="file" accept="application/pdf" className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])} />
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
        <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5">{t("convert.dropzone.subtitle")}</p>
      </div>
      <div className="flex items-center gap-3">
        <button type="button" disabled={disabled} className="btn-secondary text-xs px-3 py-1.5 gap-1.5">
          <Upload className="w-3 h-3" />
          {t("convert.dropzone.browse")}
        </button>
        <span className="text-xs text-zinc-300 dark:text-zinc-700 select-none">
          Press <kbd className="px-1 py-0.5 text-[10px] border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 font-mono">U</kbd> to browse
        </span>
      </div>
    </div>
  );
}

function UploadProgress({ filename, progress }) {
  return (
    <div className="border border-indigo-200 dark:border-indigo-500/20 bg-indigo-50/40 dark:bg-indigo-500/5 px-4 py-3 space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-indigo-700 dark:text-indigo-300 truncate max-w-xs">{filename}</span>
        <span className="text-xs text-zinc-400 tabular-nums ml-4 shrink-0">{progress}%</span>
      </div>
      <div className="h-0.5 bg-indigo-100 dark:bg-indigo-500/20 overflow-hidden">
        <div className="h-full bg-indigo-500 transition-all duration-150" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

function ConvertPage() {
  const { t } = useTranslation();
  const { user, loading: authLoading } = useAuth();

  const [docs,           setDocs]           = useState([]);
  const [loadingDocs,    setLoadingDocs]    = useState(true);
  const [selectedFile,   setSelectedFile]   = useState(null);   // preview
  const [previewUrl,     setPreviewUrl]     = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [converting,     setConverting]     = useState(new Set());

  // ── New feature state ──
  const [searchQuery,    setSearchQuery]    = useState("");
  const [checkedFiles,   setCheckedFiles]   = useState(new Set()); // bulk select
  const [sortKey,        setSortKey]        = useState("date");
  const [sortDir,        setSortDir]        = useState("desc");
  const [elapsedTimes,   setElapsedTimes]   = useState({});       // filename → seconds

  const pollRef          = useRef(null);
  const elapsedRef       = useRef(null);
  const processingStart  = useRef({});                             // filename → Date.now()

  // ── Data loading ────────────────────────────────────────────────────────

  const loadDocs = async () => {
    try {
      const data = await fetchDocuments();
      if (Array.isArray(data)) setDocs(data);
    } catch { toast.error(t("convert.errors.loadFailed")); }
    finally { setLoadingDocs(false); }
  };

  useEffect(() => {
    if (!authLoading && user) loadDocs();
    else if (!authLoading && !user) setLoadingDocs(false);
  }, [authLoading, user]);

  // ── Status polling ───────────────────────────────────────────────────────

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
              if (old?.status === "processing" && d.status === "done") {
                toast.success(t("convert.toasts.done", { filename: d.filename }));
                delete processingStart.current[d.filename];
              }
              if (old?.status === "processing" && d.status === "failed") {
                toast.error(t("convert.toasts.failed", { filename: d.filename }));
                delete processingStart.current[d.filename];
              }
            });
            return data;
          });
        } catch {}
      }, 3000);
    }
    if (!hasProcessing && pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    return () => { if (pollRef.current && !hasProcessing) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [docs]);

  // ── Live elapsed timer ───────────────────────────────────────────────────

  useEffect(() => {
    const processingDocs = docs.filter((d) => d.status === "processing");

    // Record start time for newly-processing files
    processingDocs.forEach((d) => {
      if (!processingStart.current[d.filename])
        processingStart.current[d.filename] = Date.now();
    });

    if (processingDocs.length > 0 && !elapsedRef.current) {
      elapsedRef.current = setInterval(() => {
        const now = Date.now();
        setElapsedTimes(
          Object.fromEntries(
            Object.entries(processingStart.current).map(([name, start]) => [
              name, Math.floor((now - start) / 1000),
            ])
          )
        );
      }, 1000);
    }
    if (processingDocs.length === 0 && elapsedRef.current) {
      clearInterval(elapsedRef.current);
      elapsedRef.current = null;
      setElapsedTimes({});
    }
    return () => {};
  }, [docs]);

  useEffect(() => () => {
    if (pollRef.current)   clearInterval(pollRef.current);
    if (elapsedRef.current) clearInterval(elapsedRef.current);
  }, []);

  // ── Keyboard shortcut: U = open file picker ──────────────────────────────

  useEffect(() => {
    const handler = (e) => {
      if (e.key === "u" && !e.ctrlKey && !e.metaKey && !e.altKey &&
          document.activeElement.tagName !== "INPUT" &&
          document.activeElement.tagName !== "TEXTAREA") {
        document.getElementById("hidden-file-trigger")?.click();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // ── Sort toggle ──────────────────────────────────────────────────────────

  const handleSort = (key) => {
    if (sortKey === key) setSortDir((d) => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
  };

  // ── Filtered + sorted docs ───────────────────────────────────────────────

  const filteredDocs = sortDocs(
    docs.filter((d) => d.filename.toLowerCase().includes(searchQuery.toLowerCase())),
    sortKey, sortDir
  );

  // ── Actions ──────────────────────────────────────────────────────────────

  const handleUpload = async (file) => {
    setUploadProgress({ filename: file.name, progress: 0 });
    try {
      await uploadDocument(file, (p) => setUploadProgress((prev) => ({ ...prev, progress: p })));
      toast.success(t("convert.toasts.uploaded", { filename: file.name }));
      await loadDocs();
    } catch { toast.error(t("convert.errors.uploadFailed")); }
    finally { setUploadProgress(null); }
  };

  const handleConvert = async (filename) => {
    setConverting((prev) => new Set(prev).add(filename));
    processingStart.current[filename] = Date.now();
    try {
      await convertDocument(filename);
      setDocs((prev) => prev.map((d) => d.filename === filename ? { ...d, status: "processing" } : d));
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? t("convert.errors.convertFailed"));
      delete processingStart.current[filename];
    } finally {
      setConverting((prev) => { const s = new Set(prev); s.delete(filename); return s; });
    }
  };

  const handleSelect = async (filename) => {
    if (selectedFile === filename) { setSelectedFile(null); setPreviewUrl(null); return; }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(filename); setPreviewUrl(null);
    try { setPreviewUrl(await getPreviewBlob(filename)); }
    catch { toast.error(t("convert.errors.previewFailed")); }
  };

  const handleDelete = async (filename) => {
    try {
      await deleteDocument(filename);
      setDocs((prev) => prev.filter((d) => d.filename !== filename));
      setCheckedFiles((prev) => { const s = new Set(prev); s.delete(filename); return s; });
      if (selectedFile === filename) { if (previewUrl) URL.revokeObjectURL(previewUrl); setSelectedFile(null); setPreviewUrl(null); }
      toast.success(t("convert.toasts.deleted"));
    } catch { toast.error(t("convert.errors.deleteFailed")); }
  };

  // ── Bulk actions ──────────────────────────────────────────────────────────

  const toggleCheck = (e, filename) => {
    e.stopPropagation();
    setCheckedFiles((prev) => {
      const s = new Set(prev);
      s.has(filename) ? s.delete(filename) : s.add(filename);
      return s;
    });
  };

  const toggleCheckAll = () => {
    if (checkedFiles.size === filteredDocs.length) setCheckedFiles(new Set());
    else setCheckedFiles(new Set(filteredDocs.map((d) => d.filename)));
  };

  const bulkConvert = async () => {
    const targets = [...checkedFiles].filter((fn) => {
      const doc = docs.find((d) => d.filename === fn);
      return doc && (doc.status === "pending" || doc.status === "failed");
    });
    await Promise.all(targets.map((fn) => handleConvert(fn)));
    setCheckedFiles(new Set());
  };

  const bulkDelete = async () => {
    const targets = [...checkedFiles];
    await Promise.all(targets.map((fn) => handleDelete(fn)));
    setCheckedFiles(new Set());
  };

  const hasConvertable = [...checkedFiles].some((fn) => {
    const doc = docs.find((d) => d.filename === fn);
    return doc && (doc.status === "pending" || doc.status === "failed");
  });

  if (authLoading) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Hidden trigger for keyboard shortcut */}
      <input id="hidden-file-trigger" type="file" accept="application/pdf" className="hidden"
        onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])} />

      {/* Page header */}
      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-5">
        <h1 className="text-xl font-semibold tracking-tight">{t("convert.title")}</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">{t("convert.subtitle")}</p>
      </div>

      {/* Main layout */}
      <div className={`flex flex-col ${selectedFile ? "lg:flex-row lg:gap-6" : ""}`}>

        {/* Left: upload + file list */}
        <div className={`space-y-4 ${selectedFile ? "lg:w-[46%] lg:shrink-0" : "w-full"}`}>

          <Dropzone onFile={handleUpload} disabled={!!uploadProgress} />
          {uploadProgress && <UploadProgress filename={uploadProgress.filename} progress={uploadProgress.progress} />}

          {/* File table */}
          <div>
            {/* List header row: label + search */}
            <div className="flex items-center justify-between gap-3 mb-3">
              <p className="section-label">{t("convert.yourFiles")}{!loadingDocs && docs.length > 0 && ` (${docs.length})`}</p>
              {docs.length > 0 && (
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-400 pointer-events-none" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Filter files…"
                    className="field-input pl-7 py-1 text-xs w-44"
                  />
                  {searchQuery && (
                    <button onClick={() => setSearchQuery("")}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 transition-colors">
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              )}
            </div>

            <div className="border border-zinc-200 dark:border-zinc-800">
              {/* Column headers (sortable) */}
              {!loadingDocs && docs.length > 0 && (
                <div className="grid grid-cols-[1.5rem_1fr_auto_auto] gap-3 items-center px-4 py-2 bg-zinc-50 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
                  <button onClick={toggleCheckAll} className="flex items-center justify-center text-zinc-300 dark:text-zinc-700 hover:text-indigo-500 transition-colors">
                    {checkedFiles.size > 0 && checkedFiles.size === filteredDocs.length
                      ? <CheckSquare className="w-3.5 h-3.5 text-indigo-500" />
                      : <div className={`w-3.5 h-3.5 border ${checkedFiles.size > 0 ? "border-indigo-400 bg-indigo-50 dark:bg-indigo-500/10" : "border-zinc-300 dark:border-zinc-700"}`} />
                    }
                  </button>
                  <SortHeader label="File"   colKey="name"   sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortHeader label="Status" colKey="status" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortHeader label="Date"   colKey="date"   sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                </div>
              )}

              {loadingDocs && (
                <>
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="flex items-center justify-between gap-3 px-4 py-3.5 border-b last:border-0 border-zinc-100 dark:border-zinc-800">
                      <div className="flex items-center gap-2.5 flex-1 min-w-0">
                        <div className="skel w-4 h-4 shrink-0" />
                        <div className="skel h-3 flex-1 max-w-[200px]" />
                      </div>
                      <div className="flex gap-2">
                        <div className="skel h-3 w-14" />
                        <div className="skel h-6 w-16" />
                      </div>
                    </div>
                  ))}
                </>
              )}

              {!loadingDocs && docs.length === 0 && !uploadProgress && (
                <div className="px-4 py-14 flex flex-col items-center text-center">
                  <FileText className="w-7 h-7 text-zinc-300 dark:text-zinc-700 mb-3" />
                  <p className="text-sm font-medium mb-1">{t("convert.empty.title")}</p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xs leading-relaxed">
                    {t("convert.empty.body")}
                  </p>
                </div>
              )}

              {!loadingDocs && filteredDocs.length === 0 && docs.length > 0 && (
                <div className="px-4 py-10 text-center">
                  <p className="text-sm text-zinc-400">No files match "{searchQuery}"</p>
                  <button onClick={() => setSearchQuery("")} className="text-xs text-indigo-500 hover:underline mt-1">Clear filter</button>
                </div>
              )}

              {!loadingDocs && filteredDocs.length > 0 && (
                <ul>
                  {filteredDocs.map((doc) => {
                    const isConverting = converting.has(doc.filename);
                    const busy        = isConverting || doc.status === "processing";
                    const isSelected  = selectedFile === doc.filename;
                    const isChecked   = checkedFiles.has(doc.filename);
                    const elapsed     = elapsedTimes[doc.filename];

                    return (
                      <li
                        key={doc.filename}
                        onClick={() => handleSelect(doc.filename)}
                        className={[
                          "group flex items-center gap-3 px-4 py-3 border-b border-zinc-100 dark:border-zinc-800 last:border-0 cursor-pointer transition-colors",
                          isSelected
                            ? "bg-indigo-50/60 dark:bg-indigo-500/8 border-l-2 border-l-indigo-500 !pl-[14px]"
                            : isChecked
                            ? "bg-zinc-50 dark:bg-zinc-800/40"
                            : "hover:bg-zinc-50/60 dark:hover:bg-zinc-900/40",
                        ].join(" ")}
                      >
                        {/* Checkbox */}
                        <div onClick={(e) => toggleCheck(e, doc.filename)}
                          className="shrink-0 flex items-center justify-center w-4 h-4 cursor-pointer">
                          {isChecked
                            ? <CheckSquare className="w-3.5 h-3.5 text-indigo-500" />
                            : <div className="w-3.5 h-3.5 border border-zinc-300 dark:border-zinc-700 opacity-0 group-hover:opacity-100 transition-opacity" />
                          }
                        </div>

                        {/* File info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <FileText className={`w-3.5 h-3.5 shrink-0 ${isSelected ? "text-indigo-500" : "text-zinc-300 dark:text-zinc-600"}`} />
                            <p className="text-sm truncate">{doc.filename}</p>
                          </div>
                          <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5 ml-5">
                            {(doc.size / 1024).toFixed(1)} KB
                          </p>
                        </div>

                        {/* Status */}
                        <div className="shrink-0">
                          <StatusText status={doc.status} elapsed={elapsed} />
                        </div>

                        {/* Date */}
                        <p className="text-xs text-zinc-400 dark:text-zinc-500 shrink-0 w-20 text-right tabular-nums">
                          {new Date(doc.last_modified * 1000).toLocaleDateString()}
                        </p>

                        {/* Actions */}
                        <div className="flex items-center gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                          {doc.status === "pending" && (
                            <button onClick={() => handleConvert(doc.filename)} disabled={busy} className="btn-primary text-xs px-2.5 py-1 gap-1">
                              {isConverting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                              {t("convert.actions.convert")}
                            </button>
                          )}
                          {doc.status === "failed" && (
                            <button onClick={() => handleConvert(doc.filename)} disabled={busy} className="btn-secondary text-xs px-2.5 py-1 gap-1">
                              {isConverting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                              {t("convert.actions.retry")}
                            </button>
                          )}
                          {doc.status === "done" && (
                            <button onClick={() => downloadDocument(doc.filename.replace(/\.pdf$/, ".docx"))}
                              className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30 hover:bg-emerald-50 dark:hover:bg-emerald-500/10 transition-colors"
                              style={{ borderRadius: 2 }}>
                              <Download className="w-3 h-3" />
                              {t("convert.actions.downloadPdf")}
                            </button>
                          )}
                          <button onClick={() => handleDelete(doc.filename)}
                            className="p-1 text-zinc-300 dark:text-zinc-700 hover:text-red-500 dark:hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}

              {/* ── Bulk action bar ── */}
              {checkedFiles.size > 0 && (
                <div className="flex items-center justify-between gap-3 px-4 py-2.5 bg-indigo-50 dark:bg-indigo-500/10 border-t border-indigo-200 dark:border-indigo-500/20 animate-fade-in">
                  <span className="text-xs font-medium text-indigo-700 dark:text-indigo-300">
                    {checkedFiles.size} selected
                  </span>
                  <div className="flex items-center gap-2">
                    {hasConvertable && (
                      <button onClick={bulkConvert} className="btn-primary text-xs px-3 py-1 gap-1">
                        <Zap className="w-3 h-3" />
                        Convert selected
                      </button>
                    )}
                    <button onClick={bulkDelete} className="btn-danger text-xs px-3 py-1 gap-1">
                      <Trash2 className="w-3 h-3" />
                      Delete selected
                    </button>
                    <button onClick={() => setCheckedFiles(new Set())}
                      className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors">
                      Clear
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: PDF preview panel */}
        {selectedFile && (
          <div className="flex-1 min-w-0 animate-fade-in">
            <div className="border border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-50 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
                <p className="text-xs font-medium truncate text-zinc-600 dark:text-zinc-300 max-w-[200px]">{selectedFile}</p>
                <div className="flex items-center gap-3 shrink-0">
                  <button onClick={() => downloadDocument(selectedFile)}
                    className="text-xs text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 transition-colors">
                    {t("convert.actions.downloadPdf")}
                  </button>
                  <button onClick={() => { setSelectedFile(null); setPreviewUrl(null); }}
                    className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="p-4">
                {previewUrl ? (
                  <PDFViewer fileUrl={previewUrl} />
                ) : (
                  <div className="py-16 flex items-center justify-center gap-2 text-sm text-zinc-400">
                    <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
                    {t("convert.previewLoading")}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ConvertPage;

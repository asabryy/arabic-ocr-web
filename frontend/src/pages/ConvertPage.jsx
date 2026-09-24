import React, { useState, useEffect, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import toast from "react-hot-toast";
import {
  FileText, Loader2, Zap, Trash2, Download, X,
  Search, ChevronUp, ChevronDown, ChevronsUpDown, CheckSquare,
} from "lucide-react";
import {
  fetchDocuments, uploadDocument, deleteDocument,
  convertDocument, getPreviewBlob, downloadDocument,
  fetchConversionProgress,
} from "../api/docs";
import PDFViewer from "../components/pdf/PDFViewer";
import Dropzone from "../components/upload/Dropzone";
import UsageMeter from "../components/usage/UsageMeter";
import PlanBadge from "../components/usage/PlanBadge";
import { useUsage } from "../hooks/useUsage";
import { openFeedback } from "../api/feedback";
import { emitUsageChanged } from "../api/client";

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtElapsed(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

const STATUS_ORDER = { processing: 0, pending: 1, partial: 1, failed: 2, done: 3 };

// A document longer than the plan's per-document limit is converted a batch at a
// time. Each batch is stored as its own file, `book__p11-20.pdf`, which is how the
// outputs avoid overwriting each other — so the list has to fold those back under
// the document they came from instead of showing them as separate uploads.
const PART_RE = /^(.+)__p(\d+)-(\d+)\.([A-Za-z0-9]+)$/;

function parsePart(filename) {
  const m = PART_RE.exec(filename ?? "");
  if (!m) return null;
  return { source: `${m[1]}.${m[4]}`, start: Number(m[2]), end: Number(m[3]) };
}

/** "book.pdf · Pages 11–20" — a batch's own filename is not what the user uploaded. */
function friendlyName(t, filename) {
  const part = parsePart(filename);
  return part
    ? `${part.source} · ${t("convert.partial.pages", { start: part.start, end: part.end })}`
    : filename;
}

function groupParts(docs) {
  const byParent = {};
  docs.forEach((doc) => {
    const part = parsePart(doc.filename);
    if (!part) return;
    (byParent[part.source] ||= []).push({ ...part, doc });
  });
  Object.values(byParent).forEach((list) => list.sort((a, b) => a.start - b.start));
  return byParent;
}

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
    partial:    "status-processing",
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
  const { usage, loading: usageLoading } = useUsage();

  const [docs,           setDocs]           = useState([]);
  const [loadingDocs,    setLoadingDocs]    = useState(true);
  const [selectedFile,   setSelectedFile]   = useState(null);   // preview
  const [previewUrl,     setPreviewUrl]     = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [converting,     setConverting]     = useState(new Set());
  const [progress,       setProgress]       = useState({});        // filename → batch progress

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

  // Which pages of each document are already done. Held server-side, so "continue
  // from page 41" survives a reload or a different device. Refreshed on load and
  // after anything that changes it — not on the 3s status poll, which does not.
  const loadProgress = async () => {
    try {
      const data = await fetchConversionProgress();
      const byName = {};
      (data?.items ?? []).forEach((item) => { byName[item.filename] = item; });
      setProgress(byName);
    } catch {
      // A missing progress read degrades the page to the plain list; not worth an
      // error toast on top of whatever else is already failing.
      setProgress({});
    }
  };

  useEffect(() => {
    if (!authLoading && user) { loadDocs(); loadProgress(); }
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
                toast.success(t("convert.toasts.done", { filename: friendlyName(t, d.filename) }));
                delete processingStart.current[d.filename];
              }
              if (old?.status === "processing" && d.status === "failed") {
                toast.error(t("convert.toasts.failed", { filename: friendlyName(t, d.filename) }));
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
      if (e.key !== "u" || e.ctrlKey || e.metaKey || e.altKey) return;

      // activeElement can be null while the document is being torn down.
      const el = document.activeElement;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;

      // ConvertPage stays mounted behind every modal, so without this the OS file
      // picker opens on top of an open dialog.
      if (document.querySelector('[role="dialog"]')) return;

      document.getElementById("hidden-file-trigger")?.click();
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

  const partsByParent = groupParts(docs);

  // Batches belong under their document, not beside it.
  const rootDocs = docs.filter((d) => !parsePart(d.filename));

  const filteredDocs = sortDocs(
    rootDocs.filter((d) => d.filename.toLowerCase().includes(searchQuery.toLowerCase())),
    sortKey, sortDir
  );

  /** A batch's own status stands in for the document's while it is running. */
  const effectiveStatus = (doc) => {
    const parts = partsByParent[doc.filename];
    if (!parts?.length) return doc.status;
    if (parts.some((p) => p.doc.status === "processing")) return "processing";
    if (parts.some((p) => p.doc.status === "failed")) return "failed";
    const prog = progress[doc.filename];
    if (prog && prog.remaining_pages === 0 && parts.every((p) => p.doc.status === "done"))
      return "done";
    return "partial";
  };



  // ── Actions ──────────────────────────────────────────────────────────────

  const handleUpload = async (file) => {
    setUploadProgress({ filename: file.name, progress: 0 });
    try {
      const res = await uploadDocument(file, (p) => setUploadProgress((prev) => ({ ...prev, progress: p })));
      toast.success(t("convert.toasts.uploaded", { filename: file.name }));
      if (usage && res?.pages > usage.max_doc_pages) {
        toast(t("convert.warnings.tooManyPages", { pages: res.pages, limit: usage.max_doc_pages }), { icon: "⚠️" });
      }
      await loadDocs();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : t("convert.errors.uploadFailed"));
    }
    finally { setUploadProgress(null); }
  };

  const handleConvert = async (filename, range) => {
    setConverting((prev) => new Set(prev).add(filename));
    processingStart.current[filename] = Date.now();
    try {
      const res = await convertDocument(filename, range ?? {});
      if (res?.partial) {
        // Say exactly what was taken and what is left, rather than letting the user
        // assume a 211-page book is on its way.
        const key = res.remaining_pages > 0 ? "queued" : "queuedFinal";
        toast(t(`convert.partial.${key}`, {
          filename,
          start: res.start_page,
          end: res.end_page,
          remaining: res.remaining_pages,
        }), { icon: "📄" });
        // The batch file carries the status and the clock from here on.
        delete processingStart.current[filename];
        await loadDocs();
        await loadProgress();
      } else {
        setDocs((prev) => prev.map((d) => d.filename === filename ? { ...d, status: "processing" } : d));
      }
      emitUsageChanged();
    } catch (err) {
      delete processingStart.current[filename];
      if (err?.quotaHandled) return; // LimitModal is already showing the 402 details
      const detail = err?.response?.data?.detail;
      toast.error(
        (typeof detail === "string" ? detail : detail?.message) ?? t("convert.errors.convertFailed")
      );
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

  // The worker names the output from the stem (rsplit on the last dot), so a
  // case-sensitive /\.pdf$/ replace missed "report.PDF" — the app then requested
  // the original upload and handed the user their scanned PDF as the deliverable.
  const docxNameFor = (filename) => filename.replace(/\.[^.]+$/, "") + ".docx";

  // `name` is taken as given — the preview pane downloads the original PDF, the
  // file row downloads the converted .docx.
  const safeDownload = async (name) => {
    try {
      await downloadDocument(name);
    } catch {
      toast.error(t("convert.errors.downloadFailed"));
    }
  };

  const handleDownload = async (filename) => {
    try {
      await downloadDocument(docxNameFor(filename));
    } catch {
      // Previously an unhandled rejection: a failed download at the exact moment
      // the product delivers value produced no feedback at all.
      toast.error(t("convert.errors.downloadFailed"));
    }
  };

  const handleDelete = async (filename) => {
    try {
      await deleteDocument(filename);
      // Deleting a document takes its batches with it server-side, so reload
      // rather than filtering one row out of a stale list.
      setDocs((prev) => prev.filter(
        (d) => d.filename !== filename && parsePart(d.filename)?.source !== filename
      ));
      loadProgress();
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
    const targets = [...checkedFiles]
      .map((fn) => rootDocs.find((d) => d.filename === fn))
      .filter((doc) => doc && ["pending", "failed", "partial"].includes(effectiveStatus(doc)));
    // Each click takes the next batch of a long document, so a bulk convert moves
    // every selected document one batch forward rather than pretending to finish it.
    await Promise.all(targets.map((doc) => {
      const prog = progress[doc.filename];
      const range = prog?.next_start_page != null && prog.total_pages > prog.max_doc_pages
        ? { startPage: prog.next_start_page, endPage: prog.next_end_page }
        : undefined;
      return handleConvert(doc.filename, range);
    }));
    setCheckedFiles(new Set());
  };

  const bulkDelete = async () => {
    const targets = [...checkedFiles];
    await Promise.all(targets.map((fn) => handleDelete(fn)));
    setCheckedFiles(new Set());
  };

  const hasConvertable = [...checkedFiles].some((fn) => {
    const doc = rootDocs.find((d) => d.filename === fn);
    return doc && ["pending", "failed", "partial"].includes(effectiveStatus(doc));
  });

  if (authLoading) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Hidden trigger for keyboard shortcut */}
      <input id="hidden-file-trigger" type="file" accept="application/pdf" className="hidden"
        onChange={(e) => {
          const picked = e.target.files?.[0];
          // Reset first: without it the input keeps its value, so choosing the same
          // file again fires no change event and the upload silently does nothing.
          e.target.value = "";
          if (picked) handleUpload(picked);
        }} />

      {/* Page header */}
      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-5 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight">{t("convert.title")}</h1>
            {user?.plan && <PlanBadge plan={user.plan} />}
          </div>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">{t("convert.subtitle")}</p>
        </div>
        <UsageMeter usage={usage} loading={usageLoading} />
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
              <p className="section-label">{t("convert.yourFiles")}{!loadingDocs && rootDocs.length > 0 && ` (${rootDocs.length})`}</p>
              {rootDocs.length > 0 && (
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
              {!loadingDocs && rootDocs.length > 0 && (
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

              {!loadingDocs && rootDocs.length === 0 && !uploadProgress && (
                <div className="px-4 py-14 flex flex-col items-center text-center">
                  <FileText className="w-7 h-7 text-zinc-300 dark:text-zinc-700 mb-3" />
                  <p className="text-sm font-medium mb-1">{t("convert.empty.title")}</p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xs leading-relaxed">
                    {t("convert.empty.body")}
                  </p>
                </div>
              )}

              {!loadingDocs && filteredDocs.length === 0 && rootDocs.length > 0 && (
                <div className="px-4 py-10 text-center">
                  <p className="text-sm text-zinc-400">No files match "{searchQuery}"</p>
                  <button onClick={() => setSearchQuery("")} className="text-xs text-indigo-500 hover:underline mt-1">Clear filter</button>
                </div>
              )}

              {!loadingDocs && filteredDocs.length > 0 && (
                <ul>
                  {filteredDocs.map((doc) => {
                    const parts       = partsByParent[doc.filename] ?? [];
                    const prog        = progress[doc.filename];
                    const status      = effectiveStatus(doc);
                    const isConverting = converting.has(doc.filename);
                    const busy        = isConverting || status === "processing";
                    const isSelected  = selectedFile === doc.filename;
                    const isChecked   = checkedFiles.has(doc.filename);
                    const elapsed     = elapsedTimes[doc.filename]
                      ?? elapsedTimes[parts.find((p) => p.doc.status === "processing")?.doc.filename];
                    // Documents longer than the plan's per-document limit go through
                    // in batches; the row has to show how far through it is.
                    const batched     = !!prog?.total_pages
                      && (prog.total_pages > prog.max_doc_pages || parts.length > 0);
                    const nextStart   = prog?.next_start_page;
                    const nextEnd     = prog?.next_end_page;
                    const failedPart  = parts.find((p) => p.doc.status === "failed");
                    // A failed batch is retried at its own range; otherwise the button
                    // takes the next run of pages that has not been converted yet.
                    const nextRange   = !batched
                      ? undefined
                      : failedPart
                      ? { startPage: failedPart.start, endPage: failedPart.end }
                      : nextStart != null
                      ? { startPage: nextStart, endPage: nextEnd }
                      : null;
                    const canConvert  = batched
                      ? nextRange != null
                      : status === "pending" || status === "failed";

                    return (
                      <li key={doc.filename} className="border-b border-zinc-100 dark:border-zinc-800 last:border-0">
                      <div
                        onClick={() => handleSelect(doc.filename)}
                        className={[
                          "group flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors",
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
                            {batched && (
                              <span className="ml-2">
                                ·{" "}
                                {prog.converted_pages === 0
                                  ? t("convert.partial.plan", {
                                      total: prog.total_pages, batch: prog.max_doc_pages,
                                    })
                                  : prog.remaining_pages === 0
                                  ? t("convert.partial.complete", { total: prog.total_pages })
                                  : t("convert.partial.progress", {
                                      converted: prog.converted_pages, total: prog.total_pages,
                                    })}
                              </span>
                            )}
                          </p>
                        </div>

                        {/* Status */}
                        <div className="shrink-0">
                          <StatusText status={status} elapsed={elapsed} />
                        </div>

                        {/* Date */}
                        <p className="text-xs text-zinc-400 dark:text-zinc-500 shrink-0 w-20 text-right tabular-nums">
                          {new Date(doc.last_modified * 1000).toLocaleDateString()}
                        </p>

                        {/* Actions */}
                        <div className="flex items-center gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                          {canConvert && (
                            <button
                              onClick={() => handleConvert(doc.filename, nextRange ?? undefined)}
                              disabled={busy}
                              className={status === "failed" ? "btn-secondary text-xs px-2.5 py-1 gap-1" : "btn-primary text-xs px-2.5 py-1 gap-1"}
                            >
                              {isConverting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                              {status === "failed"
                                ? t("convert.actions.retry")
                                : nextRange
                                ? t("convert.partial.convertNext", {
                                    start: nextRange.startPage, end: nextRange.endPage,
                                  })
                                : t("convert.actions.convert")}
                            </button>
                          )}
                          {status === "failed" && (
                            /* The one place a broken conversion can be reported while
                               the user still has the failing document in front of them. */
                            <button
                              onClick={() =>
                                openFeedback({
                                  category: "bug",
                                  page: `/convert (failed: ${doc.filename})`,
                                })
                              }
                              className="text-xs font-medium px-2 py-1 text-zinc-400 hover:text-indigo-500 transition-colors"
                            >
                              {t("convert.actions.reportProblem")}
                            </button>
                          )}
                          {status === "done" && parts.length === 0 && (
                            <button onClick={() => handleDownload(doc.filename)}
                              className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30 hover:bg-emerald-50 dark:hover:bg-emerald-500/10 transition-colors"
                              style={{ borderRadius: 2 }}>
                              <Download className="w-3 h-3" />
                              {t("convert.actions.downloadDocx")}
                            </button>
                          )}
                          <button onClick={() => handleDelete(doc.filename)}
                            className="p-1 text-zinc-300 dark:text-zinc-700 hover:text-red-500 dark:hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Batches. Each one is a Word file of its own — that is what
                          keeps a second range from overwriting the first. */}
                      {parts.length > 0 && (
                        <div className="px-4 pb-3 ml-5 flex flex-wrap items-center gap-1.5">
                          {parts.map(({ start, end, doc: part }) => (
                            <span key={part.filename}
                              className="inline-flex items-center gap-1.5 text-xs px-2 py-1 border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
                              <span className="tabular-nums text-zinc-500 dark:text-zinc-400">
                                {t("convert.partial.pages", { start, end })}
                              </span>
                              {part.status === "done" ? (
                                <button onClick={() => handleDownload(part.filename)}
                                  className="inline-flex items-center gap-1 font-medium text-emerald-700 dark:text-emerald-400 hover:underline">
                                  <Download className="w-3 h-3" />
                                  {t("convert.actions.downloadDocx")}
                                </button>
                              ) : part.status === "failed" ? (
                                <button onClick={() => handleConvert(doc.filename, { startPage: start, endPage: end })}
                                  className="inline-flex items-center gap-1 font-medium text-amber-600 dark:text-amber-400 hover:underline">
                                  <Zap className="w-3 h-3" />
                                  {t("convert.actions.retry")}
                                </button>
                              ) : (
                                <StatusText status={part.status} elapsed={elapsedTimes[part.filename]} />
                              )}
                            </span>
                          ))}
                          <span className="text-xs text-zinc-400 dark:text-zinc-600">
                            {t("convert.partial.hint")}
                          </span>
                        </div>
                      )}
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
                  <button onClick={() => safeDownload(selectedFile)}
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

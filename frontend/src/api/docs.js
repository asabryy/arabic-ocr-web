import { createApiClient } from "./client";

const baseUrl = import.meta.env.VITE_DOC_API_URL?.replace(/\/$/, "");

export const docApi = createApiClient(`${baseUrl}/api/doc-manager/v1`);

export const fetchDocuments = async () => {
  const res = await docApi.get("/documents");
  return res.data;
};

export const uploadDocument = async (file, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  const res = await docApi.post("/upload", formData, {
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });
  return res.data;
};

export const deleteDocument = async (filename) => {
  const res = await docApi.delete("/documents", { params: { filename } });
  return res.data;
};

/**
 * Queue a conversion.
 *
 * With no range, a document inside the plan's per-document limit is converted
 * whole; a longer one converts its next unconverted batch, and the response says
 * which pages were taken (`start_page`/`end_page`), what is left
 * (`remaining_pages`), where to resume (`next_start_page`) and which Word file it
 * will land in (`output_filename`).
 */
export const convertDocument = async (filename, { startPage, endPage } = {}) => {
  const params = { filename };
  if (startPage != null) params.start_page = startPage;
  if (endPage != null) params.end_page = endPage;
  const res = await docApi.post("/convert", null, { params });
  return res.data;
};

/**
 * Which pages of each document have already been converted, and where to pick up.
 * The ranges live on the server, so "continue from page 41" survives a reload.
 * {items: [{filename, total_pages, converted_pages, remaining_pages, ranges,
 *           next_start_page, next_end_page, max_doc_pages, partial}],
 *  max_doc_pages, plan}
 */
export const fetchConversionProgress = async (filename) => {
  const res = await docApi.get("/conversion-progress", {
    params: filename ? { filename } : undefined,
  });
  return res.data;
};

export const getPreviewBlob = async (filename) => {
  const res = await docApi.get("/preview", {
    params: { filename },
    responseType: "blob",
  });
  return URL.createObjectURL(res.data);
};

export const downloadDocument = async (filename) => {
  const res = await docApi.get("/download", {
    params: { filename },
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

export const downloadDocx = async (filename) => {
  const docxName = `${filename.replace(/\.[^.]+$/, "")}.docx`;
  const res = await docApi.get("/download", {
    params: { filename: docxName },
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = docxName;
  a.click();
  URL.revokeObjectURL(url);
};

// ── Plan usage ─────────────────────────────────────────────────────────────

/** {plan, used_today, daily_limit, max_doc_pages, resets_at} */
export const fetchUsage = async () => {
  const res = await docApi.get("/usage");
  return res.data;
};

// ── Anonymous trial (landing page; no auth) ────────────────────────────────

export const uploadTrial = async (file, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  const res = await docApi.post("/trial", formData, {
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total));
    },
  });
  return res.data; // {trial_id, pages_total, max_pages, status}
};

export const fetchTrialStatus = async (trialId) => {
  const res = await docApi.get(`/trial/${trialId}/status`);
  return res.data;
};

export const downloadTrialDocx = async (trialId, downloadName) => {
  const res = await docApi.get(`/trial/${trialId}/download`, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = downloadName;
  a.click();
  URL.revokeObjectURL(url);
};

import axios from "axios";

const baseUrl = import.meta.env.VITE_DOC_API_URL?.replace(/\/$/, "");

export const docApi = axios.create({
  baseURL: `${baseUrl}/api/doc-manager/v1`,
});

docApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

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

export const convertDocument = async (filename) => {
  const res = await docApi.post("/convert", null, { params: { filename } });
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

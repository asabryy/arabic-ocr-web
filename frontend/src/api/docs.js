// src/api/docs.js
import axios from "axios";

const baseUrl = import.meta.env.VITE_DOC_API_URL?.replace(/\/$/, "");

export const docApi = axios.create({
  baseURL: `${baseUrl}/api/doc-manager/v1`,
});

// Fetch list of user's documents
export const fetchUserDocuments = async (userId) => {
  const res = await docApi.get("/documents", {
    params: { user_id: userId },
  });
  return res.data;
};

// Upload a file
export const uploadDocument = async (file, userId) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", userId);
  const res = await docApi.post("/upload", formData);
  return res.data;
};

// Delete a file
export const deleteDocument = async (filename, userId) => {
  const res = await docApi.delete("/documents", {
    params: { user_id: userId, filename },
  });
  return res.data;
};

// ✅ Corrected: Get signed URL for preview or download
export const getDownloadUrl = async (filename, userId) => {
  const res = await docApi.get("/download", {
    params: { user_id: userId, filename },
  });
  return res.data.url;
};

// Save per-file options
export const saveDocumentOptions = async (filename, userId, options) => {
  const res = await docApi.post("/documents/options", options, {
    params: { user_id: userId, filename },
  });
  return res.data;
};

// src/components/FileExplorer.jsx
import React, { useEffect, useState, useRef } from "react";
import { useAuth } from "../../auth/AuthContext";
import { Document, Page, pdfjs } from "react-pdf";
import {
  fetchUserDocuments,
  uploadDocument,
  deleteDocument,
  getDownloadUrl,
  getPreviewUrl,
} from "../../api/docs";

import PDFViewer from "../pdf/PDFViewer";



import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";


function FileExplorer() {
  const { user, loading } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const fileInputRef = useRef();

  const fetchDocs = async () => {
    if (!user?.id) {
      console.warn("User ID missing. Skipping fetch.");
      return;
    }

    try {
      const data = await fetchUserDocuments(user.id);
      if (Array.isArray(data)) {
        setDocuments(data);
        setError(null);
      } else {
        throw new Error("Invalid response format.");
      }
    } catch (err) {
      console.error("Fetch user documents failed:", err);
      setError("Unable to load documents.");
    }
  };

  useEffect(() => {
    if (!loading && user?.id) {
      console.log("Fetching documents for user ID:", user.id);
      fetchDocs();
    }
  }, [loading, user?.id]);

  const handleSelect = async (filename) => {
    try {
        const url = getPreviewUrl(filename, user.id); // Proxy endpoint
        setSelected(filename);
        setPreviewUrl(url);
    } catch (err) {
        console.error("Preview failed:", err);
        setError("Could not preview file.");
    }
  };

  const handleDelete = async (filename) => {
    try {
      await deleteDocument(filename, user.id);
      setDocuments((docs) => docs.filter((doc) => doc.filename !== filename));
      if (selected === filename) {
        setSelected(null);
        setPreviewUrl(null);
      }
    } catch (err) {
      console.error("Delete failed:", err);
      setError("Failed to delete document.");
    }
  };

  const handleDownload = async (filename) => {
    try {
        const url = getDownloadUrl(filename, user.id); // Redirect to R2
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
    } catch (err) {
        console.error("Download failed:", err);
        setError("Failed to download file.");
    }
  };

  const handleFileDrop = async (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) await handleUpload(file);
  };

  const handleUpload = async (file) => {
    if (!user?.id) {
      console.warn("Upload failed: user ID is missing.");
      return;
    }

    try {
      await uploadDocument(file, user.id);
      fetchDocs();
    } catch (err) {
      console.error("Upload error:", err);
      setError("File upload failed.");
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  if (loading) return <p className="text-content-muted">Loading user info...</p>;
  if (!user?.id) return <p className="text-red-500">User is not authenticated.</p>;
  if (error) return <p className="text-red-500">{error}</p>;

  return (
    <div
      onDrop={handleFileDrop}
      onDragOver={(e) => e.preventDefault()}
      className="border border-dashed border-gray-300 rounded-lg p-4 space-y-4"
    >
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Your Files</h3>
        <button
          className="bg-primary text-white px-3 py-1 rounded"
          onClick={() => fileInputRef.current.click()}
        >
          Upload
        </button>
        <input
          type="file"
          hidden
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept="application/pdf"
        />
      </div>

      {documents.length === 0 ? (
        <p className="text-content-muted">No documents uploaded yet.</p>
      ) : (
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.filename}
              className={`p-3 border rounded-lg flex items-center justify-between ${
                selected === doc.filename
                  ? "bg-primary-light text-white"
                  : "bg-white dark:bg-gray-800"
              }`}
            >
              <div
                onClick={() => handleSelect(doc.filename)}
                className="flex-1 cursor-pointer"
              >
                <div className="font-medium">{doc.filename}</div>
                <div className="text-sm text-gray-500">
                  {(doc.size / 1024).toFixed(1)} KB —{" "}
                  {new Date(doc.last_modified).toLocaleString()}
                </div>
              </div>
              <div className="flex space-x-2 ml-4">
                <button
                  className="text-blue-500 hover:underline"
                  onClick={() => handleDownload(doc.filename)}
                >
                  Download
                </button>
                <button
                  className="text-red-500 hover:underline"
                  onClick={() => handleDelete(doc.filename)}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

        {previewUrl && (
        <div className="mt-4 border rounded-lg overflow-hidden bg-white dark:bg-gray-900 p-4">
            <h4 className="text-md font-semibold mb-2">PDF Preview</h4>
            <PDFViewer fileUrl={previewUrl} />
        </div>
        )}
    </div>
  );
}

export default FileExplorer;

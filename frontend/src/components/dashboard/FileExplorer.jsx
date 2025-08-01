import React, { useEffect, useState, useRef } from "react";
import { useAuth } from "../../auth/AuthContext";
import { Document, Page, pdfjs } from "react-pdf";
import {
  fetchUserDocuments,
  uploadDocument,
  deleteDocument,
  getDownloadUrl,
} from "../../api/docs";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// PDF Worker config
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

function FileExplorer() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const fileInputRef = useRef();

  const fetchDocs = async () => {
    try {
      const data = await fetchUserDocuments(user.id);
      if (Array.isArray(data)) {
        setDocuments(data);
        setError(null);
      } else {
        throw new Error("Invalid response");
      }
    } catch (err) {
      console.error("Fetch error:", err);
      setError("⚠️ Unable to load documents.");
    }
  };

  useEffect(() => {
    if (user?.id) fetchDocs();
  }, [user]);

  const handleSelect = (filename) => {
    setSelected(filename);
    setPreviewUrl(getDownloadUrl(filename, user.id));
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
      console.error("Delete failed", err);
    }
  };

  const handleDownload = (filename) => {
    const link = document.createElement("a");
    link.href = getDownloadUrl(filename, user.id);
    link.download = filename;
    link.click();
  };

  const handleFileDrop = async (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) await handleUpload(file);
  };

  const handleUpload = async (file) => {
    try {
      await uploadDocument(file, user.id);
      fetchDocs();
    } catch (err) {
      console.error("Upload error", err);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) handleUpload(file);
  };

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
                selected === doc.filename ? "bg-primary-light text-white" : "bg-white dark:bg-gray-800"
              }`}
            >
              <div onClick={() => handleSelect(doc.filename)} className="flex-1 cursor-pointer">
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
          <div className="overflow-auto max-h-[600px] border border-gray-200 dark:border-gray-700">
            <Document file={previewUrl} onLoadError={console.error}>
              <Page pageNumber={1} />
            </Document>
          </div>
        </div>
      )}
    </div>
  );
}

export default FileExplorer;

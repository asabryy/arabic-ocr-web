import React, { useState } from "react";
import axios from "axios";

export default function ArabicOCRApp() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);
      setDownloadUrl(null);
      const response = await axios.post("http://localhost:8000/upload", formData, {
        responseType: "blob",
      });

      const blob = new Blob([response.data], {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      const url = window.URL.createObjectURL(blob);
      setDownloadUrl(url);
    } catch (err) {
      alert("Failed to process file");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <div className="bg-white shadow-lg rounded-2xl p-6 max-w-md w-full">
        <h1 className="text-2xl font-bold text-center mb-4">Arabic OCR Converter</h1>
        <form onSubmit={handleUpload} className="flex flex-col gap-4">
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files[0])}
            className="border border-gray-300 rounded px-3 py-2"
            required
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
            disabled={loading}
          >
            {loading ? "Processing..." : "Upload & Convert"}
          </button>
        </form>
        {downloadUrl && (
          <div className="mt-4 text-center">
            <a
              href={downloadUrl}
              download="arabic_ocr_output.docx"
              className="text-blue-600 hover:underline"
            >
              Download Converted DOCX
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

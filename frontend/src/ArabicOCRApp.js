import React, { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [docxPath, setDocxPath] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setDocxPath(null);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setError(null);
    setDocxPath(null);

    try {
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL || "http://localhost:8000"}/ocr`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );
      const downloadPath = response.data.docx_path;
      setDocxPath(`${process.env.REACT_APP_API_URL || "http://localhost:8000"}${downloadPath}`);
    } catch (err) {
      console.error("OCR request failed:", err);
      setError("Could not process the PDF. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App" style={{ padding: "2rem", fontFamily: "Arial, sans-serif" }}>
      <h1>Arabic OCR PDF Converter</h1>
      <form onSubmit={handleSubmit}>
        <input type="file" accept="application/pdf" onChange={handleFileChange} />
        <button type="submit" disabled={loading || !file}>
          Upload PDF
        </button>
      </form>

      {loading && <p>⏳ Processing your PDF, please wait...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
      {docxPath && (
        <p>
          ✅ Done! <a href={docxPath} download>Download your DOCX</a>
        </p>
      )}
    </div>
  );
}

export default App;

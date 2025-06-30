import React, { useState } from 'react';
import FileUpload from './components/FileUpload';
import Loader from './components/Loader';
import DownloadLink from './components/DownloadLink';
import { uploadPDF } from './services/api';

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

    setLoading(true);
    setError(null);
    try {
      const downloadPath = await uploadPDF(file);
      setDocxPath(downloadPath);
    } catch (err) {
      console.error("Upload failed:", err);
      setError("Failed to upload PDF. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App" style={{ padding: "2rem", fontFamily: "Arial, sans-serif" }}>
      <h1>Arabic OCR PDF Converter</h1>
      <FileUpload onFileChange={handleFileChange} onSubmit={handleSubmit} loading={loading} />
      {loading && <Loader />}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {docxPath && <DownloadLink docxPath={docxPath} />}
    </div>
  );
}

export default App;

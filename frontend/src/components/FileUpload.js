import React from 'react';

const FileUpload = ({ onFileChange, onSubmit, loading }) => (
  <form onSubmit={onSubmit}>
    <input type="file" accept="application/pdf" onChange={onFileChange} />
    <button type="submit" disabled={loading}>Upload PDF</button>
  </form>
);

export default FileUpload;
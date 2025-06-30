import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const uploadPDF = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API_BASE}/ocr`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return `${API_BASE}${response.data.docx_path}`;
};
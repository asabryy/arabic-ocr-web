import axios from "axios";

export const ocrApi = axios.create({
  baseURL: "/api/ocr",
});
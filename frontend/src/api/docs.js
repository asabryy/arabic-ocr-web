import axios from "axios";

export const docsApi = axios.create({
  baseURL: "/api/docs",
});

import axios from "axios";
export const authApi = axios.create({ baseURL: "https://auth-service-k63w.onrender.com/api/auth/v1" });
import { createApiClient } from "../../api/client";

const baseUrl = import.meta.env.VITE_AUTH_API_URL?.replace(/\/$/, "");

export const authApi = createApiClient(`${baseUrl}/api/auth/v1`);

export const registerUser = async ({ name, email, password }) => {
  const response = await authApi.post("/register", { name, email, password });
  return response.data;
};

export const loginUser = async ({ email, password }) => {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const response = await authApi.post("/token", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return response.data.access_token;
};

export const getCurrentUser = async (token) => {
  const response = await authApi.get("/users/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const updateCurrentUser = async (token, data) => {
  const response = await authApi.put("/users/me", data, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const googleAuth = async (credential) => {
  const response = await authApi.post("/auth/google", { credential });
  return response.data.access_token;
};

export const forgotPassword = async (email) => {
  const response = await authApi.post("/forgot-password", { email });
  return response.data;
};

export const resetPassword = async ({ token, new_password }) => {
  const response = await authApi.post("/reset-password", { token, new_password });
  return response.data;
};

export const refreshToken = async () => {
  const response = await authApi.post("/refresh");
  return response.data.access_token;
};

/**
 * Ask for a fresh verification email. The server rate-limits this to once every
 * 5 minutes and answers 400 if the address is already verified.
 */
export const resendVerificationEmail = async () => {
  const response = await authApi.post("/verify-email/resend");
  return response.data;
};

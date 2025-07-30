import axios from "axios";

const baseUrl = import.meta.env.VITE_AUTH_API_URL?.replace(/\/$/, "");

export const authApi = axios.create({
  baseURL: `${baseUrl}/api/auth/v1`,
});


// Register user
export const registerUser = async ({ name, email, password }) => {
  const response = await authApi.post("/register", {
    name,
    email,
    password,
  });
  return response.data;
};

export const loginUser = async ({ email, password }) => {
  const form = new URLSearchParams();
  form.append("username", email); // must be 'username' per FastAPI expectation
  form.append("password", password);

  const response = await authApi.post("/token", form, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  return response.data.access_token;
};

// Get current user using the provided token
export const getCurrentUser = async (token) => {
  const response = await authApi.get("/users/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const updateCurrentUser = async (token, data) => {
  const response = await authApi.put("/users/me", data, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
};
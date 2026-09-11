import axios from "axios";

// ── Tiny event bus (no extra dependency) ───────────────────────────────────
// Lets non-React code (the axios interceptor) notify React (LimitModal, UsageMeter).

const quotaListeners = new Set();
const usageListeners = new Set();

/** Subscribe to plan-quota (402) events. Returns an unsubscribe function. */
export function onQuotaExceeded(listener) {
  quotaListeners.add(listener);
  return () => quotaListeners.delete(listener);
}

export function emitQuotaExceeded(detail) {
  quotaListeners.forEach((fn) => fn(detail));
}

/** Subscribe to "usage changed" pings (after a successful convert). */
export function onUsageChanged(listener) {
  usageListeners.add(listener);
  return () => usageListeners.delete(listener);
}

export function emitUsageChanged() {
  usageListeners.forEach((fn) => fn());
}

// ── Client factory ─────────────────────────────────────────────────────────

/**
 * Axios instance with the Bearer token attached and plan-quota handling:
 * a 402 carrying `{code, message, limit, used, plan}` is broadcast to
 * `onQuotaExceeded` listeners (the LimitModal) and marked `err.quotaHandled`
 * so callers can skip their generic error toast.
 */
export function createApiClient(baseURL) {
  const api = axios.create({ baseURL });

  api.interceptors.request.use((config) => {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  api.interceptors.response.use(
    (res) => res,
    (err) => {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 402 && detail && typeof detail === "object" && detail.code) {
        emitQuotaExceeded(detail);
        err.quotaHandled = true;
      }
      return Promise.reject(err);
    }
  );

  return api;
}

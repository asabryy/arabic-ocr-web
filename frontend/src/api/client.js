import axios from "axios";

// ── Tiny event bus (no extra dependency) ───────────────────────────────────
// Lets non-React code (the axios interceptor) notify React (LimitModal, UsageMeter).

const quotaListeners = new Set();
const usageListeners = new Set();
const sessionListeners = new Set();

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

/** Subscribe to "the session is over" — a 401 that a refresh could not rescue. */
export function onSessionExpired(listener) {
  sessionListeners.add(listener);
  return () => sessionListeners.delete(listener);
}

function emitSessionExpired() {
  localStorage.removeItem("access_token");
  sessionListeners.forEach((fn) => fn());
}

// ── Token refresh ──────────────────────────────────────────────────────────
// Access tokens expire after 30 minutes. Without this the app kept showing the
// user as signed in while every request failed: the document list froze, a
// conversion sat on "Converting" forever, and Download did nothing at all.
//
// One shared in-flight refresh, so a burst of concurrent 401s (the poll plus a
// usage fetch, say) produces a single /refresh call rather than a stampede.
let refreshInFlight = null;

function refreshAccessToken(instance) {
  if (!refreshInFlight) {
    refreshInFlight = instance
      .post("/refresh", null, { _skipAuthRetry: true })
      .then((res) => {
        const next = res?.data?.access_token;
        if (!next) throw new Error("No token in refresh response");
        localStorage.setItem("access_token", next);
        return next;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
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
    async (err) => {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const config = err?.config;

      if (status === 402 && detail && typeof detail === "object" && detail.code) {
        emitQuotaExceeded(detail);
        err.quotaHandled = true;
        return Promise.reject(err);
      }

      // Retry once behind a fresh token. `_retried` prevents a loop when the
      // refreshed token is itself rejected; `_skipAuthRetry` keeps the refresh
      // call from recursing into itself.
      if (status === 401 && config && !config._retried && !config._skipAuthRetry) {
        config._retried = true;
        try {
          const next = await refreshAccessToken(api);
          config.headers = { ...config.headers, Authorization: `Bearer ${next}` };
          return api.request(config);
        } catch {
          emitSessionExpired();
          err.sessionExpired = true;
          return Promise.reject(err);
        }
      }

      if (status === 401) {
        emitSessionExpired();
        err.sessionExpired = true;
      }

      return Promise.reject(err);
    }
  );

  return api;
}

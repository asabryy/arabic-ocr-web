import { authApi } from "../features/auth/authservice";

// Tiny event bus, mirroring onQuotaExceeded in api/client.js: lets any component
// (user menu, a failed conversion row) open the feedback modal without prop-drilling
// through MainLayout.
const listeners = new Set();

/** Subscribe to "open the feedback modal" requests. Returns an unsubscribe function. */
export function onFeedbackRequested(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Open the feedback modal. `context` may carry {category, page}. */
export function openFeedback(context = {}) {
  listeners.forEach((fn) => fn(context));
}

/**
 * Send a support/feedback message. Works signed-in or anonymous — anonymous callers
 * must supply an email so we can reply.
 */
export const sendFeedback = async ({ category, message, email, page, website }) => {
  const res = await authApi.post("/feedback", {
    category,
    message,
    email: email || undefined,
    page: page || undefined,
    website: website || undefined,
  });
  return res.data;
};

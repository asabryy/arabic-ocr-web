/**
 * A displayable message from an axios error.
 *
 * FastAPI's `detail` is a string for explicit HTTPExceptions but a list of objects
 * for 422 validation errors. Rendering that list as a React child throws inside the
 * toast and, with no error boundary above it, blanks the page.
 */
export function errorText(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (typeof first?.msg === "string") return first.msg;
  }
  if (typeof detail?.message === "string") return detail.message;
  return fallback;
}

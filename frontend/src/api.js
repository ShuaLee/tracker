// Thin fetch wrapper for backend/accounts' /api/auth/ endpoints.
// Session-cookie auth (not tokens) - every request needs credentials:
// "include", and every unsafe one needs Django's CSRF header once the
// csrftoken cookie exists (see ensureCsrfCookie, called once on app start).

// Must be the same *site* as the page (localhost, not 127.0.0.1): the session
// cookie is SameSite=Lax, so the browser won't send it cross-site, and
// document.cookie can't read another host's csrftoken.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function apiFetch(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (method !== "GET") {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    // No body (e.g. some error responses) - leave data as null.
  }

  return { ok: response.ok, status: response.status, data };
}

// Turns a DRF error body into one readable string. DRF returns either
// {"detail": "..."} or {"field": ["msg", ...], "non_field_errors": [...]},
// and nested serializers (me/'s profile) nest the same shape.
export function errorMessage(response, fallback = "Something went wrong.") {
  const data = response.data;
  if (response.status === 429) return data?.detail || "Too many attempts - try again later.";
  if (!data || typeof data !== "object") return fallback;
  if (typeof data.detail === "string") return data.detail;

  const lines = [];
  const walk = (value, label) => {
    if (Array.isArray(value)) {
      const text = value.filter((item) => typeof item === "string").join(" ");
      if (text) lines.push(label ? `${label}: ${text}` : text);
      value.filter((item) => typeof item === "object").forEach((item) => walk(item, label));
    } else if (value && typeof value === "object") {
      Object.entries(value).forEach(([key, inner]) =>
        walk(inner, key === "non_field_errors" ? label : key.replaceAll("_", " ")),
      );
    } else if (typeof value === "string") {
      lines.push(label ? `${label}: ${value}` : value);
    }
  };
  walk(data, "");
  return lines.length ? lines.join("\n") : fallback;
}

// --- session ---------------------------------------------------------------

export function ensureCsrfCookie() {
  return apiFetch("/api/auth/csrf/");
}

export function fetchMe() {
  return apiFetch("/api/auth/me/");
}

export function login(email, password) {
  return apiFetch("/api/auth/login/", { method: "POST", body: { email, password } });
}

export function logout() {
  return apiFetch("/api/auth/logout/", { method: "POST" });
}

// keepCurrent: true signs out every *other* session and keeps this one.
export function logoutAll(keepCurrent) {
  return apiFetch("/api/auth/logout-all/", { method: "POST", body: { keep_current: keepCurrent } });
}

export function fetchSecurityEvents() {
  return apiFetch("/api/auth/security-events/");
}

// { currencies: [{value, label}], timezones: [...] }
export function fetchOptions() {
  return apiFetch("/api/auth/options/");
}

// --- registration & email verification -------------------------------------

export function register(email, password, displayName) {
  return apiFetch("/api/auth/register/", {
    method: "POST",
    body: { email, password, display_name: displayName },
  });
}

export function verifyEmail(uid, email, token) {
  return apiFetch("/api/auth/verify-email/", { method: "POST", body: { uid, email, token } });
}

export function resendVerification(email) {
  return apiFetch("/api/auth/resend-verification/", { method: "POST", body: { email } });
}

// --- password --------------------------------------------------------------

export function changePassword(currentPassword, newPassword) {
  return apiFetch("/api/auth/password/change/", {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
  });
}

export function requestPasswordReset(email) {
  return apiFetch("/api/auth/password/reset/", { method: "POST", body: { email } });
}

export function confirmPasswordReset(uid, token, newPassword) {
  return apiFetch("/api/auth/password/reset/confirm/", {
    method: "POST",
    body: { uid, token, new_password: newPassword },
  });
}

// --- account ---------------------------------------------------------------

export function updateProfile(profile) {
  return apiFetch("/api/auth/me/", { method: "PATCH", body: { profile } });
}

export function changeEmail(newEmail, currentPassword) {
  return apiFetch("/api/auth/email/change/", {
    method: "POST",
    body: { new_email: newEmail, current_password: currentPassword },
  });
}

// Permanently deletes the account and everything it owns.
export function deleteAccount(currentPassword) {
  return apiFetch("/api/auth/delete-account/", {
    method: "POST",
    body: { current_password: currentPassword },
  });
}

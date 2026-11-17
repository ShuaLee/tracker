// Thin fetch wrapper for backend/accounts' /api/auth/ endpoints.
// Session-cookie auth (not tokens) - every request needs credentials:
// "include", and every unsafe one needs Django's CSRF header once the
// csrftoken cookie exists (see ensureCsrfCookie, called once on app start).

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

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

export function updateProfile(profile) {
  return apiFetch("/api/auth/me/", { method: "PATCH", body: { profile } });
}

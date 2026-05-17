import axios from "axios";

/**
 * Origin for media URLs (profile photos). API calls use relative paths when
 * `REACT_APP_API_BASE` is unset so the CRA dev proxy can keep cookies on the same site.
 */
export const API_ORIGIN =
  process.env.REACT_APP_API_ORIGIN || "http://127.0.0.1:8000";

const baseURL = process.env.REACT_APP_API_BASE ?? "";

const ACCESS_KEY = "smartagile_access_token";
const REFRESH_KEY = "smartagile_refresh_token";

/** @deprecated use setAuthTokens */
export function setTabAuthToken(token) {
  setAccessToken(token);
}

export function setAccessToken(token) {
  try {
    if (token) sessionStorage.setItem(ACCESS_KEY, token);
    else sessionStorage.removeItem(ACCESS_KEY);
  } catch {
    /* ignore */
  }
}

export function setRefreshToken(token) {
  try {
    if (token) sessionStorage.setItem(REFRESH_KEY, token);
    else sessionStorage.removeItem(REFRESH_KEY);
  } catch {
    /* ignore */
  }
}

export function setAuthTokens({ access, refresh }) {
  setAccessToken(access ?? null);
  setRefreshToken(refresh ?? null);
}

export function clearTabAuthToken() {
  clearAuthTokens();
}

export function clearAuthTokens() {
  setAccessToken(null);
  setRefreshToken(null);
}

function getAccessToken() {
  try {
    return sessionStorage.getItem(ACCESS_KEY);
  } catch {
    return null;
  }
}

function getRefreshToken() {
  try {
    return sessionStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

/** For desktop agent pairing: read current JWTs from sessionStorage. */
export { getAccessToken, getRefreshToken };

export const api = axios.create({
  baseURL,
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
});

api.interceptors.request.use((config) => {
  const t = getAccessToken();
  if (t) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

let refreshPromise = null;

async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const { data } = await axios.post(
        `${baseURL}/api/token/refresh/`,
        { refresh },
        {
          headers: { "Content-Type": "application/json" },
          withCredentials: true,
        }
      );
      if (data?.access) {
        setAccessToken(data.access);
        return data.access;
      }
      clearAuthTokens();
      return null;
    } catch {
      clearAuthTokens();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const orig = error.config;
    if (
      error.response?.status === 401 &&
      orig &&
      !orig._authRetry &&
      getRefreshToken() &&
      !String(orig.url || "").includes("/api/token/refresh/")
    ) {
      orig._authRetry = true;
      const access = await refreshAccessToken();
      if (access) {
        orig.headers = orig.headers || {};
        orig.headers.Authorization = `Bearer ${access}`;
        return api(orig);
      }
    }
    return Promise.reject(error);
  }
);

export function mediaUrl(path) {
  if (!path) return "";
  const s = String(path);
  if (s.startsWith("http")) return s;
  return `${API_ORIGIN}${s}`;
}

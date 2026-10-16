import axios from "axios";
import mockAdapter from "../mocks/mockAdapter";

export const USE_MOCKS = process.env.REACT_APP_USE_MOCKS === "true";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000/api",
  // En mode mock, aucune requete ne part vers le backend Django.
  ...(USE_MOCKS && { adapter: mockAdapter }),
});

// Attache automatiquement le token JWT a chaque requete
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Rafraichit automatiquement le token via /api/auth/refresh/ en cas de 401,
// puis rejoue la requete d'origine une seule fois.
let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;

    if (response?.status !== 401 || config._retried) {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      return Promise.reject(error);
    }

    config._retried = true;

    try {
      refreshPromise =
        refreshPromise ||
        axios.post(
          `${api.defaults.baseURL}/auth/refresh/`,
          { refresh: refreshToken },
          { adapter: api.defaults.adapter }
        );
      const { data } = await refreshPromise;
      localStorage.setItem("access_token", data.access);
      if (data.refresh) {
        localStorage.setItem("refresh_token", data.refresh);
      }
      config.headers.Authorization = `Bearer ${data.access}`;
      return api(config);
    } catch (refreshError) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      window.location.assign("/login");
      return Promise.reject(refreshError);
    } finally {
      refreshPromise = null;
    }
  }
);

// Le backend peut renvoyer une URL absolue ("http://.../api/reports/1/download/")
// ou un chemin incluant déjà le préfixe "/api" : on évite de le doubler.
function resolveDownloadUrl(url) {
  if (/^https?:\/\//.test(url)) return url;
  const basePath = new URL(api.defaults.baseURL, window.location.origin).pathname.replace(/\/$/, "");
  return basePath && url.startsWith(`${basePath}/`) ? url.slice(basePath.length) : url;
}

function filenameFromHeaders(headers, fallback) {
  const disposition = headers?.["content-disposition"] || "";
  const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
  return match ? decodeURIComponent(match[1]) : fallback;
}

// Télécharge un fichier protégé par JWT (un simple <a href> n'enverrait pas le token).
export async function downloadFile(url, { params, filename } = {}) {
  const response = await api.get(resolveDownloadUrl(url), { params, responseType: "blob" });
  const blobUrl = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filenameFromHeaders(response.headers, filename || "export");
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(blobUrl);
}

export default api;

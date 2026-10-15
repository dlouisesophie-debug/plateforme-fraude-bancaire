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
      window.location.assign("/login");
      return Promise.reject(refreshError);
    } finally {
      refreshPromise = null;
    }
  }
);

export default api;

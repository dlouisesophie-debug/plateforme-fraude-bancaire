import axios from "axios";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000/api",
});

// Attache automatiquement le token JWT a chaque requete
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// TODO Etudiant 3 : ajouter un interceptor de reponse pour rafraichir
// automatiquement le token via /api/auth/refresh/ en cas de 401.

export default api;

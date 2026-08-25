import axios from "axios";
import {
  mockAlerts,
  mockDashboardKpis,
  mockMLModels,
  mockReports,
  mockTransactions,
  mockUser,
  mockUsersList,
  delay,
} from "../mocks/mockData";

const USE_MOCKS = process.env.REACT_APP_USE_MOCKS === "true";

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

/**
 * Couche de mock — utilisee tant que le backend n'est pas branche.
 *
 * Chaque fonction retourne la MEME FORME de donnees que ce que renverra
 * l'API reelle (voir backend, dossier serializers.py de chaque app). Le jour ou le backend
 * est pret :
 *   1. Mettre REACT_APP_USE_MOCKS=false dans .env
 *   2. Supprimer ce bloc (ou le laisser, il ne sera juste plus utilise)
 * Aucune modification necessaire dans les pages/composants.
 */
export const mockApi = {
  login: async (username, password) =>
    delay({ access: "mock-access-token", refresh: "mock-refresh-token", user: mockUser }),

  getTransactions: async () => delay({ count: mockTransactions.length, results: mockTransactions }),

  getAlerts: async () => delay({ count: mockAlerts.length, results: mockAlerts }),

  getDashboardKpis: async () => delay(mockDashboardKpis),

  confirmAlert: async (id) => delay({ id, status: "confirmed" }),
  rejectAlert: async (id) => delay({ id, status: "rejected" }),

  getReports: async () => delay({ count: mockReports.length, results: mockReports }),
  generateReport: async (payload) =>
    delay({ id: mockReports.length + 1, ...payload, created_at: new Date().toISOString() }),

  getMLModels: async () => delay({ count: mockMLModels.length, results: mockMLModels }),

  getUsers: async () => delay({ count: mockUsersList.length, results: mockUsersList }),
};

export const USE_MOCKS_FLAG = USE_MOCKS;

export default api;

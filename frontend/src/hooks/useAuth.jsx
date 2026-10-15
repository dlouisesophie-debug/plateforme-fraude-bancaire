import { createContext, useCallback, useContext, useState } from "react";
import api from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    Boolean(localStorage.getItem("access_token"))
  );

  const login = useCallback(async (username, password) => {
    const { data } = await api.post("/auth/login/", { username, password });
    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth doit etre utilise a l'interieur de <AuthProvider>");
  }
  return context;
}

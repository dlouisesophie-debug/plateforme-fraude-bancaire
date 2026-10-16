import { createContext, useCallback, useContext, useEffect, useState } from "react";
import api from "../services/api";

const AuthContext = createContext(null);

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem("user")) || null;
  } catch {
    return null;
  }
}

function storeUser(user) {
  if (user) localStorage.setItem("user", JSON.stringify(user));
  else localStorage.removeItem("user");
}

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    Boolean(localStorage.getItem("access_token"))
  );
  const [user, setUser] = useState(readStoredUser);
  const [userLoading, setUserLoading] = useState(isAuthenticated && !readStoredUser());

  const fetchMe = useCallback(async () => {
    setUserLoading(true);
    try {
      const { data } = await api.get("/auth/me/");
      storeUser(data);
      setUser(data);
    } catch {
      // /auth/me/ indisponible : on garde l'utilisateur connu (menu minimal sinon).
    } finally {
      setUserLoading(false);
    }
  }, []);

  // Session ouverte avant l'ajout de "user" au login : on récupère le profil.
  useEffect(() => {
    if (isAuthenticated && !user) fetchMe();
  }, [isAuthenticated, user, fetchMe]);

  const login = useCallback(
    async (username, password) => {
      const { data } = await api.post("/auth/login/", { username, password });
      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);
      if (data.user) {
        storeUser(data.user);
        setUser(data.user);
      } else {
        storeUser(null);
        setUser(null);
        await fetchMe();
      }
      setIsAuthenticated(true);
    },
    [fetchMe]
  );

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    storeUser(null);
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, userLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth doit être utilisé à l'intérieur de <AuthProvider>");
  }
  return context;
}

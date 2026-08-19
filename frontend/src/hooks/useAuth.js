import { useCallback, useState } from "react";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    Boolean(localStorage.getItem("access_token"))
  );

  const login = useCallback(async (username, password) => {
    const data = USE_MOCKS_FLAG
      ? await mockApi.login(username, password)
      : (await api.post("/auth/login/", { username, password })).data;

    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
  }, []);

  return { isAuthenticated, login, logout };
}

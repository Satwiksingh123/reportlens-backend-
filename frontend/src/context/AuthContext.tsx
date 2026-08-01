import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, clearToken, getToken, registerUnauthorizedHandler, setToken } from "../api/client";

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => getToken() !== null);

  useEffect(() => {
    registerUnauthorizedHandler(() => setIsAuthenticated(false));
  }, []);

  const login = async (email: string, password: string) => {
    const { access_token } = await api.login(email, password);
    setToken(access_token);
    setIsAuthenticated(true);
  };

  const register = async (email: string, password: string) => {
    await api.register(email, password);
    // registering doesn't return a token - log in right after so signup feels one-step
    await login(email, password);
  };

  const logout = () => {
    clearToken();
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

interface AuthContextType {
  isLoggedIn: boolean;
  sub: string | null;
  role: string | null;
  login: (token: string, sub: string, role: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isLoggedIn: false,
  sub: null,
  role: null,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState(() => !!localStorage.getItem("token"));
  const [sub, setSub] = useState<string | null>(() => localStorage.getItem("sub"));
  const [role, setRole] = useState<string | null>(() => localStorage.getItem("role"));

  useEffect(() => {
    setIsLoggedIn(!!localStorage.getItem("token"));
    setSub(localStorage.getItem("sub"));
    setRole(localStorage.getItem("role"));
  }, []);

  const login = useCallback((token: string, subVal: string, roleVal: string) => {
    localStorage.setItem("token", token);
    localStorage.setItem("sub", subVal);
    localStorage.setItem("role", roleVal);
    setIsLoggedIn(true);
    setSub(subVal);
    setRole(roleVal);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("sub");
    localStorage.removeItem("role");
    setIsLoggedIn(false);
    setSub(null);
    setRole(null);
    window.location.href = "/login";
  }, []);

  return (
    <AuthContext.Provider value={{ isLoggedIn, sub, role, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

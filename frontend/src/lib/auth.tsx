import { createContext, useContext, type ReactNode } from "react";
import { useAuthStatus } from "./queries";

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean;
  user: { username: string } | null;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data, isLoading } = useAuthStatus();

  const value: AuthContextType = {
    isAuthenticated: data?.authenticated ?? false,
    isLoading,
    isInitialized: data?.initialized ?? false,
    user: data?.user ?? null,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

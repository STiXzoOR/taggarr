import { Navigate, useLocation } from "@tanstack/react-router";
import { useAuth } from "~/lib/auth";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, isInitialized } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Redirect to setup if not initialized
  if (!isInitialized && location.pathname !== "/setup") {
    return <Navigate to="/setup" />;
  }

  // Redirect to login if not authenticated
  if (
    !isAuthenticated &&
    location.pathname !== "/login" &&
    location.pathname !== "/setup"
  ) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
}

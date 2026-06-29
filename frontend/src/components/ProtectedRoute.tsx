import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { ReactNode } from "react";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isLoggedIn } = useAuth();
  const location = useLocation();
  if (!isLoggedIn) {
    // Pass current path+search as ?redirect= so LoginForm can navigate back after login.
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }
  return <>{children}</>;
}

import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./useAuth";

function AuthLoading() {
  return (
    <main className="auth-loading">
      <span className="status-dot" />
      Checking your session...
    </main>
  );
}

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <AuthLoading />;

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function PublicOnlyRoute() {
  const { user, loading } = useAuth();

  if (loading) return <AuthLoading />;

  return user ? <Navigate to="/dashboard" replace /> : <Outlet />;
}

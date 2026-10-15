import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import Spinner from "../../components/ui/Spinner";
import { useSession } from "./useSession";

interface ProtectedRouteProps {
  children: ReactNode;
}

export default function ProtectedRoute({
  children,
}: ProtectedRouteProps) {
  const { isLoading, isAuthenticated } = useSession();
  const location = useLocation();

  if (isLoading) {
    return <Spinner />;
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location }}
      />
    );
  }

  return <>{children}</>;
}

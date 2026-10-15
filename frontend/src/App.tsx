import { lazy, Suspense } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  Navigate,
  useNavigate,
} from "react-router-dom";
import Spinner from "./components/ui/Spinner";
import {
  SessionProvider,
  ProtectedRoute,
  useSession,
} from "./features/auth";
import { logout as logoutRequest } from "./api/auth";
import LoginPage from "./features/auth/LoginPage";
import SignupPage from "./features/auth/SignupPage";

const UploadPage = lazy(() => import("./pages/UploadPage"));
const ScansPage = lazy(() => import("./pages/ScansPage"));
const ScanDetailPage = lazy(() => import("./pages/ScanDetailPage"));
const DashboardPage = lazy(
  () => import("./features/dashboard/DashboardPage"),
);

function NavigationBar() {
  const { isAuthenticated, clearSession } = useSession();
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      await logoutRequest();
    } catch {
      // Clear the local session even if the API request fails.
    } finally {
      clearSession();
      navigate("/login", { replace: true });
    }
  }

  return (
    <nav className="flex flex-wrap items-center gap-6 border-b px-6 py-4">
      <Link
        to="/dashboard"
        className="font-medium text-blue-600 hover:underline"
      >
        Dashboard
      </Link>

      <Link
        to="/upload"
        className="font-medium text-blue-600 hover:underline"
      >
        Upload
      </Link>

      <Link
        to="/scans"
        className="font-medium text-blue-600 hover:underline"
      >
        Scans
      </Link>

      {isAuthenticated && (
        <button
          type="button"
          onClick={handleLogout}
          className="ml-auto rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
        >
          Logout
        </button>
      )}
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <NavigationBar />

        <main className="p-6">
          <Suspense fallback={<Spinner />}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />

              <Route
                path="/"
                element={<Navigate to="/dashboard" replace />}
              />

              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/upload"
                element={
                  <ProtectedRoute>
                    <UploadPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/scans"
                element={
                  <ProtectedRoute>
                    <ScansPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/scans/:id"
                element={
                  <ProtectedRoute>
                    <ScanDetailPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="*"
                element={<Navigate to="/dashboard" replace />}
              />
            </Routes>
          </Suspense>
        </main>
      </SessionProvider>
    </BrowserRouter>
  );
}
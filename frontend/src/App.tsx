import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Spinner from "./components/ui/Spinner";

// Lazy imports so App.tsx never needs re-editing when a feature page changes,
// and each page is code-split into its own chunk.
const UploadPage = lazy(() => import("./pages/UploadPage"));
const ScansPage = lazy(() => import("./pages/ScansPage"));
const ScanDetailPage = lazy(() => import("./pages/ScanDetailPage"));
const DashboardPage = lazy(() => import("./features/dashboard/DashboardPage"));

export default function App() {
  return (
    <BrowserRouter>
      <nav className="flex gap-6 border-b px-6 py-4">
        <Link to="/dashboard" className="font-medium text-blue-600 hover:underline">
          Dashboard
        </Link>
        <Link to="/upload" className="font-medium text-blue-600 hover:underline">
          Upload
        </Link>
        <Link to="/scans" className="font-medium text-blue-600 hover:underline">
          Scans
        </Link>
      </nav>

      <main className="p-6">
        <Suspense fallback={<Spinner />}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/scans" element={<ScansPage />} />
            <Route path="/scans/:id" element={<ScanDetailPage />} />
          </Routes>
        </Suspense>
      </main>
    </BrowserRouter>
  );
}


import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { SessionProvider } from "./useSession";
import ProtectedRoute from "./ProtectedRoute";
import { http, HttpResponse } from "msw";
import { server } from "../../test/setup";

function LocationDisplay() {
  const location = useLocation();

  return <p>Current path: {location.pathname}</p>;
}

function renderProtectedRoute() {
  return render(
    <MemoryRouter initialEntries={["/upload?tab=cloud"]}>
      <SessionProvider>
        <LocationDisplay />
        <Routes>
          <Route
            path="/login"
            element={<p>Login page reached</p>}
          />
          <Route
            path="/upload"
            element={
              <ProtectedRoute>
                <p>Protected upload page</p>
              </ProtectedRoute>
            }
          />
        </Routes>
      </SessionProvider>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("redirects unauthenticated users to login", async () => {
    server.use(
      http.get("*/auth/me", () =>
        HttpResponse.json(
          { detail: "Not authenticated." },
          { status: 401 },
        ),
      ),
    );

    renderProtectedRoute();

    expect(
      await screen.findByText("Login page reached"),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("Protected upload page"),
    ).not.toBeInTheDocument();
  });

  it("shows the protected page when a session exists", async () => {
    server.use(
      http.get("*/auth/me", () =>
        HttpResponse.json({
          user_id: "protected-test-user",
          email: "demo@example.com",
          role: "Admin",
        }),
      ),
    );

    renderProtectedRoute();

    expect(
      await screen.findByText("Protected upload page"),
    ).toBeInTheDocument();
  });
});

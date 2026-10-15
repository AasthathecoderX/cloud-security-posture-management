import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { SessionProvider } from "./SessionContext";
import LoginPage from "./LoginPage";
import { server } from "../../test/setup";

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <SessionProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={<p>Dashboard page reached</p>}
          />
        </Routes>
      </SessionProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  document.cookie = "csrf_token=; Max-Age=0; path=/";

  server.use(
    http.get("*/auth/me", () => {
      document.cookie =
        "csrf_token=mock-csrf-token; path=/; SameSite=Strict";

      return HttpResponse.json(
        { detail: "Not authenticated." },
        { status: 401 },
      );
    }),

    http.post("*/auth/login", async ({ request }) => {
      if (
        request.headers.get("X-CSRF-Token") !== "mock-csrf-token"
      ) {
        return HttpResponse.json(
          { detail: "Invalid CSRF token." },
          { status: 403 },
        );
      }

      const body = (await request.json()) as {
        email: string;
        password: string;
      };

      if (
        body.email !== "demo@example.com" ||
        body.password !== "Password123!"
      ) {
        return HttpResponse.json(
          { detail: "Invalid email or password." },
          { status: 401 },
        );
      }

      return HttpResponse.json({
        user_id: "test-user-1",
        email: body.email,
        role: "Admin",
      });
    }),
  );
});

describe("LoginPage", () => {
  it("logs in successfully and navigates to the dashboard", async () => {
    const user = userEvent.setup();

    renderLoginPage();

    await user.type(
      screen.getByLabelText(/email/i),
      "demo@example.com",
    );
    await user.type(
      screen.getByLabelText(/password/i),
      "Password123!",
    );
    await user.click(
      screen.getByRole("button", { name: /sign in/i }),
    );

    expect(
      await screen.findByText("Dashboard page reached"),
    ).toBeInTheDocument();
  });

  it("shows a generic error when the credentials are invalid", async () => {
    const user = userEvent.setup();

    renderLoginPage();

    await user.type(
      screen.getByLabelText(/email/i),
      "demo@example.com",
    );
    await user.type(
      screen.getByLabelText(/password/i),
      "wrong-password",
    );
    await user.click(
      screen.getByRole("button", { name: /sign in/i }),
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Invalid email or password.");

    expect(
      screen.queryByText("Dashboard page reached"),
    ).not.toBeInTheDocument();
  });
});
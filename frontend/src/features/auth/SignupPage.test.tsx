
import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { SessionProvider } from "./useSession";
import SignupPage from "./SignupPage";
import { server } from "../../test/setup";

function renderSignupPage() {
  return render(
    <MemoryRouter initialEntries={["/signup"]}>
      <SessionProvider>
        <Routes>
          <Route path="/signup" element={<SignupPage />} />
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

    http.post("*/auth/signup", async ({ request }) => {
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

      return HttpResponse.json(
        {
          user_id: "signup-test-user",
          email: body.email,
          role: "Viewer",
        },
        { status: 201 },
      );
    }),
  );
});

describe("SignupPage", () => {
  it("creates an account and navigates to the dashboard", async () => {
    const user = userEvent.setup();

    renderSignupPage();

    await user.type(
      screen.getByLabelText(/^email$/i),
      "newuser@example.com",
    );
    await user.type(
      screen.getByLabelText(/^password$/i),
      "SecurePass123!",
    );
    await user.type(
      screen.getByLabelText(/confirm password/i),
      "SecurePass123!",
    );
    await user.click(
      screen.getByRole("button", { name: /create account/i }),
    );

    expect(
      await screen.findByText("Dashboard page reached"),
    ).toBeInTheDocument();
  });

  it("shows an error when the passwords do not match", async () => {
    const user = userEvent.setup();

    renderSignupPage();

    await user.type(
      screen.getByLabelText(/^email$/i),
      "newuser@example.com",
    );
    await user.type(
      screen.getByLabelText(/^password$/i),
      "SecurePass123!",
    );
    await user.type(
      screen.getByLabelText(/confirm password/i),
      "DifferentPass123!",
    );
    await user.click(
      screen.getByRole("button", { name: /create account/i }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Passwords do not match.",
    );
    expect(
      screen.queryByText("Dashboard page reached"),
    ).not.toBeInTheDocument();
  });
});

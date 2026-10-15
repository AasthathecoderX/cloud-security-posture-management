
import { describe, expect, it } from "vitest";
import {
  createLoginRedirectUrl,
  shouldRedirectToLogin,
} from "./authRedirect";

describe("Authentication redirect logic", () => {
  it("redirects on a 401 from a protected API endpoint", () => {
    expect(
      shouldRedirectToLogin(401, "/scans", "/scans"),
    ).toBe(true);
  });

  it("does not redirect on a login or session-check 401", () => {
    expect(
      shouldRedirectToLogin(401, "/auth/login", "/login"),
    ).toBe(false);

    expect(
      shouldRedirectToLogin(401, "/auth/me", "/dashboard"),
    ).toBe(false);
  });

  it("does not redirect for non-401 responses", () => {
    expect(
      shouldRedirectToLogin(403, "/scans", "/scans"),
    ).toBe(false);
  });

  it("preserves the intended path, query, and hash", () => {
    const url = createLoginRedirectUrl(
      "/scans/123?tab=findings#critical",
      "http://localhost:5173",
    );

    const parsedUrl = new URL(url);

    expect(parsedUrl.pathname).toBe("/login");
    expect(parsedUrl.searchParams.get("next")).toBe(
      "/scans/123?tab=findings#critical",
    );
  });
});

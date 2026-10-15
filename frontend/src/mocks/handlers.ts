import { http, HttpResponse } from "msw";
import {
  scans,
  scanDetailsById,
  attackPathsById,
  complianceById,
} from "./data";
import type { UserResponse } from "../api/types";

// Mock authentication state for local development and tests.
let mockCurrentUser: UserResponse | null = null;

function ensureMockCsrfCookie() {
  if (
    typeof document !== "undefined" &&
    !document.cookie.includes("csrf_token=")
  ) {
    document.cookie =
      "csrf_token=mock-csrf-token; path=/; SameSite=Strict";
  }
}

function hasMockCsrfToken(request: Request): boolean {
  ensureMockCsrfCookie();
  return request.headers.get("X-CSRF-Token") === "mock-csrf-token";
}

// Paths are wildcarded so handlers match regardless of API origin.
const ALLOWED_EXTENSIONS = [".json", ".yaml", ".yml"];

export const handlers = [
  // Authentication handlers
  http.get("*/auth/me", () => {
    ensureMockCsrfCookie();

    if (!mockCurrentUser) {
      return HttpResponse.json(
        { detail: "Not authenticated." },
        { status: 401 },
      );
    }

    return HttpResponse.json(mockCurrentUser);
  }),

  http.post("*/auth/login", async ({ request }) => {
    if (!hasMockCsrfToken(request)) {
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

    mockCurrentUser = {
      user_id: "mock-user-1",
      email: body.email,
      role: "Admin",
    };

    return HttpResponse.json(mockCurrentUser);
  }),

  http.post("*/auth/signup", async ({ request }) => {
    if (!hasMockCsrfToken(request)) {
      return HttpResponse.json(
        { detail: "Invalid CSRF token." },
        { status: 403 },
      );
    }

    const body = (await request.json()) as {
      email: string;
      password: string;
    };

    if (!body.email || !body.password) {
      return HttpResponse.json(
        { detail: "Email and password are required." },
        { status: 422 },
      );
    }

    mockCurrentUser = {
      user_id: "mock-user-2",
      email: body.email,
      role: "Viewer",
    };

    return HttpResponse.json(mockCurrentUser, { status: 201 });
  }),

  http.post("*/auth/logout", () => {
    mockCurrentUser = null;
    return new HttpResponse(null, { status: 204 });
  }),

  // Existing scan handlers
  http.get("*/scans", () => {
    return HttpResponse.json(scans);
  }),

  // More specific routes first so they win over "*/scans/:id".
  http.get("*/scans/:id/attack-paths", ({ params }) => {
    const detail = scanDetailsById[params.id as string];

    if (!detail) {
      return HttpResponse.json(
        { detail: "Scan not found." },
        { status: 404 },
      );
    }

    const attackPaths = attackPathsById[params.id as string];

    return HttpResponse.json(
      attackPaths ?? {
        scan_id: params.id,
        nodes: [],
        links: [],
        paths: [],
      },
    );
  }),

  http.get("*/scans/:id/compliance", ({ params }) => {
    const detail = scanDetailsById[params.id as string];

    if (!detail) {
      return HttpResponse.json(
        { detail: "Scan not found." },
        { status: 404 },
      );
    }

    const compliance = complianceById[params.id as string];

    return HttpResponse.json(
      compliance ?? {
        scan_id: params.id,
        frameworks: {
          CIS: { passed: 0, failed: 0, total: 0 },
          NIST: { passed: 0, failed: 0, total: 0 },
        },
        controls: [],
      },
    );
  }),

  http.get("*/scans/:id/findings", ({ params }) => {
    const detail = scanDetailsById[params.id as string];

    if (!detail) {
      return HttpResponse.json(
        { detail: "Scan not found." },
        { status: 404 },
      );
    }

    return HttpResponse.json(detail.findings);
  }),

  http.get("*/scans/:id", ({ params }) => {
    const detail = scanDetailsById[params.id as string];

    if (!detail) {
      return HttpResponse.json(
        { detail: "Scan not found." },
        { status: 404 },
      );
    }

    return HttpResponse.json(detail);
  }),

  http.post("*/scans/upload", async ({ request }) => {
    const form = await request.formData();
    const file = form.get("file");

    // Mirror the server's 400 for an unsupported file type.
    const name = file instanceof File ? file.name : "";
    const ext = "." + (name.split(".").pop()?.toLowerCase() ?? "");

    if (!(file instanceof File) || !ALLOWED_EXTENSIONS.includes(ext)) {
      return HttpResponse.json(
        { detail: "Unsupported file type." },
        { status: 400 },
      );
    }

    return HttpResponse.json({
      scan_id: "1",
      status: "COMPLETED",
      findings_count: scanDetailsById["1"].findings.length,
    });
  }),

  http.post("*/scans/cloud", () => {
    return HttpResponse.json({
      scan_id: "3",
      status: "COMPLETED",
      findings_count: scanDetailsById["3"].findings.length,
    });
  }),
];
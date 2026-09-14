import { http, HttpResponse } from "msw";
import { scans, scanDetailsById } from "./data";

// Paths are wildcarded (`*/scans`) so they match regardless of origin — the
// Axios client sends requests to VITE_API_BASE_URL (e.g. http://localhost:8000),
// not the page origin, so a bare "/scans" would never intercept them.
const ALLOWED_EXTENSIONS = [".json", ".yaml", ".yml"];

export const handlers = [
  http.get("*/scans", () => {
    return HttpResponse.json(scans);
  }),

  // More specific route first so it wins over "*/scans/:id".
  http.get("*/scans/:id/findings", ({ params }) => {
    const detail = scanDetailsById[params.id as string];
    if (!detail) {
      return HttpResponse.json({ detail: "Scan not found." }, { status: 404 });
    }
    return HttpResponse.json(detail.findings);
  }),

  http.get("*/scans/:id", ({ params }) => {
    const detail = scanDetailsById[params.id as string];
    if (!detail) {
      return HttpResponse.json({ detail: "Scan not found." }, { status: 404 });
    }
    return HttpResponse.json(detail);
  }),

  http.post("*/scans/upload", async ({ request }) => {
    const form = await request.formData();
    const file = form.get("file");

    // Mirror the server's 400 for an unsupported file type so the upload
    // feature's error path can be exercised against mocks.
    const name = file instanceof File ? file.name : "";
    const ext = "." + (name.split(".").pop()?.toLowerCase() ?? "");
    if (!(file instanceof File) || !ALLOWED_EXTENSIONS.includes(ext)) {
      return HttpResponse.json({ detail: "Unsupported file type." }, { status: 400 });
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
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Spinner from "../components/ui/Spinner";
import { uploadScan, scanCloudAccount } from "../api/scans";
import type { UploadResponse } from "../api/types";

const ALLOWED_EXTENSIONS = [".json", ".yaml", ".yml"];
const MAX_SIZE = 2 * 1024 * 1024; // 2 MB — the server enforces this too.

// Client-side gate so the user gets instant feedback; the backend still
// validates independently.
function validateFile(file: File): string | null {
  const extension = "." + (file.name.split(".").pop()?.toLowerCase() ?? "");
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return "Only JSON and YAML files are allowed.";
  }
  if (file.size > MAX_SIZE) {
    return "File size must be less than 2 MB.";
  }
  return null;
}

export default function UploadPage() {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  // Member 1's Axios client rejects with a plain string, so TError is string.
  const mutation = useMutation<UploadResponse, string, File>({
    mutationFn: uploadScan,
    onSuccess: () => {
      // Refresh the scans list so the new scan shows up immediately.
      queryClient.invalidateQueries({ queryKey: ["scans"] });
    },
  });

  const cloudMutation = useMutation<UploadResponse, string, void>({
     mutationFn: scanCloudAccount,
     onSuccess: () => {
       queryClient.invalidateQueries({ queryKey: ["scans"] });
     },
  });

  function selectFile(selected: File | undefined) {
    if (!selected) return;
    const validationError = validateFile(selected);
    if (validationError) {
      setError(validationError);
      setFile(null);
      return;
    }
    setError("");
    mutation.reset();
    setFile(selected);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files?.[0]);
  }

  function handleUpload() {
    if (file) mutation.mutate(file);
  }

  const errorMessage =
    error ||
    (mutation.isError
      ? typeof mutation.error === "string"
        ? mutation.error
        : "Upload failed."
      : "");

  return (
    <div className="mx-auto mt-10 max-w-2xl">
      <Card>
        <h1 className="mb-2 text-2xl font-bold">Upload Cloud Configuration</h1>
        <p className="mb-6 text-gray-600">
          Upload a JSON or YAML cloud configuration file to perform a security scan.
        </p>

        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
          }}
          className={`mb-4 cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
            isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300"
          }`}
        >
          <p className="text-gray-600">
            Drag &amp; drop a JSON or YAML file here, or click to browse
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".json,.yaml,.yml"
            className="hidden"
            onChange={(event) => selectFile(event.target.files?.[0])}
          />
        </div>

        {file && (
          <p className="mb-4">
            <strong>Selected file:</strong> {file.name}
          </p>
        )}

        {errorMessage && <p className="mb-4 text-red-600">{errorMessage}</p>}

        {mutation.isPending && (
          <div className="mb-4">
            <Spinner />
          </div>
        )}

        {mutation.isSuccess && (
          <div className="mb-4 text-green-700">
            <p>Upload successful!</p>
            <p>Findings: {mutation.data.findings_count}</p>
            <Link
              to={`/scans/${mutation.data.scan_id}`}
              className="mt-1 inline-block text-blue-600 hover:underline"
            >
              View scan details →
            </Link>
          </div>
        )}

        <Button onClick={handleUpload} disabled={!file || mutation.isPending}>
          Upload &amp; Scan
        </Button>
       <div className="mt-6 border-t pt-6">
  <h2 className="mb-2 text-lg font-semibold">Live Cloud Scan</h2>

  <p className="mb-4 text-sm text-gray-600">
    Scan your connected cloud account directly for security issues.
  </p>

  {cloudMutation.isPending && (
    <div className="mb-4">
      <Spinner />
    </div>
  )}

  {cloudMutation.isError && (
    <p className="mb-4 text-red-600">
      {cloudMutation.error || "Cloud scan failed."}
    </p>
  )}

  {cloudMutation.isSuccess && (
    <div className="mb-4 text-green-700">
      <p>
        Cloud scan completed! Findings:{" "}
        {cloudMutation.data.findings_count}
      </p>

      <Link
        to={`/scans/${cloudMutation.data.scan_id}`}
        className="mt-1 inline-block text-blue-600 hover:underline"
      >
        View scan details →
      </Link>
    </div>
  )}

       <Button
         onClick={() => cloudMutation.mutate()}
         disabled={cloudMutation.isPending}
       >
       Scan Cloud Account
       </Button>
      </div>
      </Card>
    </div>
  );
}

import client from "./client";
import type {
  ScanSummary,
  ScanDetail,
  Finding,
  UploadResponse,
} from "./types";

export const uploadScan = async (
  file: File
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await client.post(
    "/scans/upload",
    formData
  );

  return data;
};

export const scanCloudAccount = async (): Promise<UploadResponse> => {
  const { data } = await client.post("/scans/cloud");
  return data;
};

export const listScans = async (): Promise<ScanSummary[]> => {
  const { data } = await client.get("/scans");
  return data;
};

export const getScan = async (
  id: string
): Promise<ScanDetail> => {
  const { data } = await client.get(`/scans/${id}`);
  return data;
};

export const getScanFindings = async (
  id: string
): Promise<Finding[]> => {
  const { data } = await client.get(
    `/scans/${id}/findings`
  );
  return data;
};
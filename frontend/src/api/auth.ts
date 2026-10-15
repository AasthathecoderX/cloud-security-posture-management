
import client from "./client";
import type { UserResponse } from "./types";

export interface AuthCredentials {
  email: string;
  password: string;
}

function getCsrfToken(): string {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrf_token="));

  if (!cookie) {
    throw new Error("CSRF token is missing. Please try again.");
  }

  return decodeURIComponent(cookie.slice("csrf_token=".length));
}

// Bootstrap the CSRF cookie before login or signup.
// The backend intentionally returns 401 from /auth/me when logged out,
// but it also sets the CSRF cookie when one does not exist.
async function bootstrapCsrf(): Promise<void> {
  try {
    await client.get<UserResponse>("/auth/me");
  } catch {
    // A 401 is expected when the user is not signed in.
    // The request still allows the backend to set the CSRF cookie.
  }
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await client.get<UserResponse>("/auth/me");
  return response.data;
}

export async function login(
  credentials: AuthCredentials,
): Promise<UserResponse> {
  await bootstrapCsrf();

  const response = await client.post<UserResponse>(
    "/auth/login",
    credentials,
    {
      headers: { "X-CSRF-Token": getCsrfToken() },
    },
  );

  return response.data;
}

export async function signup(
  credentials: AuthCredentials,
): Promise<UserResponse> {
  await bootstrapCsrf();

  const response = await client.post<UserResponse>(
    "/auth/signup",
    credentials,
    {
      headers: { "X-CSRF-Token": getCsrfToken() },
    },
  );

  return response.data;
}

export async function logout(): Promise<void> {
  const response = await client.post(
    "/auth/logout",
    undefined,
    {
      headers: { "X-CSRF-Token": getCsrfToken() },
    },
  );

  return response.data;
}

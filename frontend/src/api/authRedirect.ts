
export function shouldRedirectToLogin(
  status: number | undefined,
  requestUrl: string,
  pathname: string,
): boolean {
  const isAuthEndpoint =
    /^\/?auth\/(login|signup|me|refresh|logout)(?:[/?#]|$)/.test(
      requestUrl,
    );

  return (
    status === 401 &&
    !isAuthEndpoint &&
    pathname !== "/login" &&
    pathname !== "/signup"
  );
}

export function createLoginRedirectUrl(
  currentPath: string,
  origin: string,
): string {
  const loginUrl = new URL("/login", origin);
  loginUrl.searchParams.set("next", currentPath);
  return loginUrl.toString();
}

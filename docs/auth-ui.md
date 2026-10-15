# Frontend Authentication

## Overview

The frontend uses cookie-based authentication. The browser sends authentication cookies with API requests through the shared Axios client. Access and refresh tokens must not be stored in local storage or session storage.

## Pages and Components

- `src/features/auth/LoginPage.tsx` — login form, error handling, and post-login navigation.
- `src/features/auth/SignupPage.tsx` — account creation and password confirmation.
- `src/features/auth/useSession.tsx` — session context and current-user state.
- `src/features/auth/ProtectedRoute.tsx` — protects authenticated pages.
- `src/api/auth.ts` — authentication API requests and CSRF headers.
- `src/api/client.ts` — shared Axios configuration and global unauthorized-response handling.

## Authentication Flow

1. The session provider requests `GET /auth/me` when it mounts.
2. If a valid session exists, the current user's ID, email, and role are loaded into session state.
3. If the user is unauthenticated, protected routes redirect to `/login`.
4. The login and signup flows bootstrap the CSRF cookie and send the `X-CSRF-Token` header with their POST requests.
5. After successful authentication, the returned user is stored in React session state and the user is redirected to the intended page or dashboard.
6. Logout calls `POST /auth/logout`, clears local session state, and navigates to the login page.

## Protected Routes

The following routes require an authenticated session:

- `/dashboard`
- `/upload`
- `/scans`
- `/scans/:id`

While the session is loading, the protected route displays a loading indicator. Unauthenticated users are redirected to `/login`, with their intended location preserved in router state.

## Unauthorized API Responses

The shared Axios response interceptor handles HTTP `401` responses from non-authentication endpoints. It redirects the browser to `/login` and preserves the current path, query string, and hash in the `next` parameter.

Authentication endpoints are excluded from this global redirect to avoid redirect loops during login, signup, and session checks.

## Security Considerations

- Authentication tokens must be issued and managed by the backend using HTTP-only cookies.
- Cookies should use `Secure` in production and an appropriate `SameSite` policy.
- State-changing authentication requests include the CSRF token in the `X-CSRF-Token` header.
- The frontend must never expose authentication tokens through local storage or API response bodies.
- Client-side route protection is a usability measure, not an authorization boundary. The backend must independently authenticate requests and enforce role-based access control.

## Testing

Authentication UI tests use Vitest, React Testing Library, and MSW. They cover login success and failure, signup success and password mismatch, protected-route behavior, and unauthorized-redirect decisions.

The development mocks are for local development and testing only. Real backend integration must be verified against the backend authentication contract before deployment.
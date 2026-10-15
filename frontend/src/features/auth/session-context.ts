import { createContext } from "react";
import type { UserResponse } from "../../api/types";

export interface SessionContextValue {
  user: UserResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  refreshSession: () => Promise<void>;
  setSession: (user: UserResponse) => void;
  clearSession: () => void;
}

// The context and its type live in their own (non-component) file: both
// SessionContext.tsx (the SessionProvider component) and useSession.ts (the
// hook) need it, and react-refresh/only-export-components requires a file
// that exports a component to export *only* components -- createContext()
// isn't one, even as a non-JSX value in an otherwise component-only file.
export const SessionContext = createContext<SessionContextValue | undefined>(
  undefined,
);

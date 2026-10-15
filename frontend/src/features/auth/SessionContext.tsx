import { useCallback, useEffect, useState, type ReactNode } from "react";
import { getCurrentUser } from "../../api/auth";
import type { UserResponse } from "../../api/types";
import { SessionContext } from "./session-context";

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshSession = useCallback(async () => {
    setIsLoading(true);

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch {
      // A 401 from /auth/me means there is no active session.
      // Other failures also leave the user unauthenticated for now.
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const setSession = useCallback((nextUser: UserResponse) => {
    setUser(nextUser);
    setIsLoading(false);
  }, []);

  const clearSession = useCallback(() => {
    setUser(null);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    // Intentional: bootstrap the session once on mount by asking the server
    // who (if anyone) the current cookie belongs to. refreshSession's first
    // synchronous statement is setIsLoading(true), which is what the
    // set-state-in-effect rule is reacting to -- but there's no React state
    // to derive this from up front (that's the whole point of the call),
    // so there's no non-effect alternative here.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshSession();
  }, [refreshSession]);

  return (
    <SessionContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        refreshSession,
        setSession,
        clearSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

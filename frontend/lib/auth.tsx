"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { apiRequest } from "@/lib/api";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  roles: string[];
  is_platform_admin: boolean;
}

interface LoginResult {
  requiresMfa: boolean;
  challengeToken: string | null;
}

interface AuthContextValue {
  user: CurrentUser | null;
  loading: boolean;
  login: (
    email: string,
    password: string,
    tenantSlug: string
  ) => Promise<LoginResult>;
  verifyMfa: (challengeToken: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const publicPaths = [
  "/login",
  "/accept-invitation",
  "/forgot-password",
  "/reset-password"
];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    try {
      setUser(await apiRequest<CurrentUser>("/auth/me"));
    } catch {
      setUser(null);
      if (!publicPaths.some((path) => pathname.startsWith(path))) {
        router.replace("/login");
      }
    } finally {
      setLoading(false);
    }
  }, [pathname, router]);

  useEffect(() => {
    if (publicPaths.some((path) => pathname.startsWith(path))) {
      setLoading(false);
      return;
    }
    void refreshUser();
  }, [pathname, refreshUser]);

  const login = useCallback(async (
    email: string,
    password: string,
    tenantSlug: string
  ): Promise<LoginResult> => {
    const response = await apiRequest<{
      authenticated: boolean;
      requires_mfa: boolean;
      mfa_challenge_token: string | null;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        tenant_slug: tenantSlug
      })
    });
    if (response.requires_mfa) {
      return {
        requiresMfa: true,
        challengeToken: response.mfa_challenge_token
      };
    }
    await refreshUser();
    router.replace("/");
    return { requiresMfa: false, challengeToken: null };
  }, [refreshUser, router]);

  const verifyMfa = useCallback(async (
    challengeToken: string,
    code: string
  ): Promise<void> => {
    await apiRequest("/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify({
        challenge_token: challengeToken,
        code
      })
    });
    await refreshUser();
    router.replace("/");
  }, [refreshUser, router]);

  const logout = useCallback(async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } finally {
      setUser(null);
      router.replace("/login");
    }
  }, [router]);

  const value = useMemo(
    () => ({ user, loading, login, verifyMfa, logout, refreshUser }),
    [user, loading, login, verifyMfa, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}

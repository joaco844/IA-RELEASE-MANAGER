import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, clearToken, getToken, setToken } from "@/lib/api";
import type { RegisterPayload, TokenResponse, User } from "@/types";

interface AuthContextValue {
  user: User | undefined;
  isLoadingUser: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = React.useState(() => Boolean(getToken()));

  const { data: user, isLoading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.get<User>("/auth/me"),
    enabled: hasToken,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const login = React.useCallback(
    async (email: string, password: string) => {
      const response = await api.post<TokenResponse>("/auth/login", { email, password });
      setToken(response.access_token);
      setHasToken(true);
      await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
    [queryClient],
  );

  const register = React.useCallback(
    async (payload: RegisterPayload) => {
      await api.post<User>("/auth/register", payload);
      await login(payload.email, payload.password);
    },
    [login],
  );

  const logout = React.useCallback(() => {
    clearToken();
    setHasToken(false);
    queryClient.clear();
  }, [queryClient]);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      isLoadingUser: hasToken && isLoading,
      isAuthenticated: hasToken,
      login,
      register,
      logout,
    }),
    [user, isLoading, hasToken, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return context;
}

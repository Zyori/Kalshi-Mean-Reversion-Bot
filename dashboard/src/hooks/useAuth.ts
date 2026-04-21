import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";

export function useAuth() {
  const qc = useQueryClient();

  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        await api.me();
        return true;
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return false;
        throw e;
      }
    },
    retry: false,
    staleTime: 60_000,
  });

  const login = useMutation({
    mutationFn: (password: string) => api.login(password),
    onSuccess: () => {
      qc.setQueryData(["auth", "me"], true);
    },
  });

  const logout = useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      qc.setQueryData(["auth", "me"], false);
      qc.clear();
    },
  });

  return {
    authed: meQuery.data,
    isLoading: meQuery.isLoading,
    login,
    logout,
  };
}

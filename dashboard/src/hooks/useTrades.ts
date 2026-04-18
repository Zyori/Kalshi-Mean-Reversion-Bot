import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useTrades(params?: {
  sport?: string;
  status?: string;
  sort_by?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ["trades", params],
    queryFn: () => api.trades(params),
    refetchInterval: 5_000,
    staleTime: 4_000,
    placeholderData: keepPreviousData,
  });
}

export function useActiveTrades() {
  return useQuery({
    queryKey: ["trades", "active"],
    queryFn: () => api.activeTrades(),
    refetchInterval: 5_000,
    staleTime: 4_000,
    placeholderData: keepPreviousData,
  });
}

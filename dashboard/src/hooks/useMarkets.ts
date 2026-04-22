import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useGames(params?: {
  sport?: string;
  status?: string;
  days_ahead?: number;
  days_back?: number;
  sort?: "asc" | "desc";
  limit?: number;
}) {
  return useQuery({
    queryKey: ["games", params],
    queryFn: () => api.games(params),
    refetchInterval: 10_000,
    staleTime: 8_000,
    placeholderData: keepPreviousData,
  });
}

export function useGame(id: number) {
  return useQuery({
    queryKey: ["games", id],
    queryFn: () => api.game(id),
    enabled: id > 0,
    refetchInterval: 10_000,
    staleTime: 8_000,
  });
}

export function useGameEvents(gameId: number) {
  return useQuery({
    queryKey: ["games", gameId, "events"],
    queryFn: () => api.gameEvents(gameId),
    refetchInterval: 10_000,
    staleTime: 8_000,
    placeholderData: keepPreviousData,
  });
}

export function useRecentEvents(params?: {
  sport?: string;
  event_type?: string;
  classification?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["events", params],
    queryFn: () => api.events(params),
    refetchInterval: 10_000,
    staleTime: 8_000,
    placeholderData: keepPreviousData,
  });
}

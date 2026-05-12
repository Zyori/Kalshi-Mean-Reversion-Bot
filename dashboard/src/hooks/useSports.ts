import { useQuery } from "@tanstack/react-query";
import { api, type SportEntry, type SportMode } from "../lib/api";

/** Source of truth for which sports the bot is engaging with. Refreshes
 * cheaply on a 30s cadence — the backing table is rarely edited at runtime
 * but we want UI to pick up flips without a full reload. */
export function useSports() {
  return useQuery({
    queryKey: ["sports"],
    queryFn: api.sports,
    refetchInterval: 30_000,
    staleTime: 25_000,
    select: (resp) => resp.sports,
  });
}

export function useActiveSports() {
  const { data, ...rest } = useSports();
  return { ...rest, data: data?.filter((s) => s.mode === "active") ?? [] };
}

export function useSportEntry(sport: string) {
  const { data } = useSports();
  return data?.find((s) => s.sport === sport);
}

export type { SportEntry, SportMode };

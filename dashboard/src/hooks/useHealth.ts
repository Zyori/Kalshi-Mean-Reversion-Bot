import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

/** Authed health surface, including per-supervisor-loop heartbeats.
 * Drives the connection pill and the optional stale-loop warning banner. */
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 10_000,
    staleTime: 8_000,
  });
}

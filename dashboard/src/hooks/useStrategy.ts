import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useStrategyCatalog() {
  return useQuery({
    queryKey: ["strategy"],
    queryFn: api.strategy,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

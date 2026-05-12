import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type FindingCreate } from "../lib/api";

/** Findings = operator-curated insights persisted into the `insights` table
 * with type=manual_finding, plus any auto-generated insights for the same
 * sport. Single timeline so the sport page shows everything we've learned. */
export function useFindings(sport?: string) {
  return useQuery({
    queryKey: ["insights", { sport }],
    queryFn: () => api.insights({ sport, limit: 50 }),
    refetchInterval: 30_000,
    staleTime: 25_000,
  });
}

export function useCreateFinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: FindingCreate) => api.createFinding(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insights"] });
    },
  });
}

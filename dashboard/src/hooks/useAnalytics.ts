import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useAnalysisSummary() {
  return useQuery({
    queryKey: ["analysis", "summary"],
    queryFn: api.analysisSummary,
    refetchInterval: 15_000,
    staleTime: 10_000,
    placeholderData: keepPreviousData,
  });
}

export function useAnalysisBySport() {
  return useQuery({
    queryKey: ["analysis", "by-sport"],
    queryFn: api.analysisBySport,
    refetchInterval: 30_000,
    staleTime: 25_000,
    placeholderData: keepPreviousData,
  });
}

export function useEquityCurve() {
  return useQuery({
    queryKey: ["analysis", "equity-curve"],
    queryFn: api.equityCurve,
    refetchInterval: 30_000,
    staleTime: 25_000,
    placeholderData: keepPreviousData,
  });
}

export function useAnalysisByEventType() {
  return useQuery({
    queryKey: ["analysis", "by-event-type"],
    queryFn: api.analysisByEventType,
    refetchInterval: 30_000,
    staleTime: 25_000,
    placeholderData: keepPreviousData,
  });
}

export function useAnalysisByMarketCategory() {
  return useQuery({
    queryKey: ["analysis", "by-market-category"],
    queryFn: api.analysisByMarketCategory,
    refetchInterval: 30_000,
    staleTime: 25_000,
    placeholderData: keepPreviousData,
  });
}

export function useRecentEventAudit() {
  return useQuery({
    queryKey: ["analysis", "recent-event-audit"],
    queryFn: api.recentEventAudit,
    refetchInterval: 30_000,
    staleTime: 25_000,
    placeholderData: keepPreviousData,
  });
}

export function useKellyComparison() {
  return useQuery({
    queryKey: ["analysis", "kelly-comparison"],
    queryFn: api.kellyComparison,
    refetchInterval: 30_000,
    staleTime: 25_000,
    placeholderData: keepPreviousData,
  });
}

export function useInsights() {
  return useQuery({
    queryKey: ["insights"],
    queryFn: () => api.insights(),
    refetchInterval: 30_000,
    staleTime: 25_000,
    placeholderData: keepPreviousData,
  });
}

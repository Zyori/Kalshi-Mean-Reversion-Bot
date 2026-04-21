import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}

export function PublicStatusPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["public", "status"],
    queryFn: api.publicStatus,
    refetchInterval: 15_000,
  });

  const alive = data?.alive === true;
  const dotClass = isError ? "bg-loss" : alive ? "bg-profit" : "bg-text-dim";
  const label = isError ? "Unreachable" : alive ? "Running" : "Unknown";

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-lg border border-border bg-surface-1 p-8 text-center shadow-lg">
        <h1 className="text-2xl font-semibold tracking-tight">Lutz</h1>
        <p className="mt-1 text-sm text-text-dim">Autonomous market scanner</p>

        <div className="mt-8 flex items-center justify-center gap-2">
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${dotClass}`} />
          <span className="text-sm font-medium">{label}</span>
        </div>

        {!isLoading && !isError && data && (
          <dl className="mt-8 grid grid-cols-2 gap-4 text-left">
            <div className="rounded-md border border-border bg-surface-0 p-3">
              <dt className="text-xs text-text-dim">Uptime</dt>
              <dd className="mt-0.5 font-mono text-sm">{formatUptime(data.uptime_seconds)}</dd>
            </div>
            <div className="rounded-md border border-border bg-surface-0 p-3">
              <dt className="text-xs text-text-dim">Sources</dt>
              <dd className="mt-0.5 font-mono text-sm">
                {data.sources_up}/{data.sources_total}
              </dd>
            </div>
          </dl>
        )}

        <p className="mt-8 text-[11px] uppercase tracking-wider text-text-dim">
          Public status · no account required
        </p>
      </div>
    </div>
  );
}

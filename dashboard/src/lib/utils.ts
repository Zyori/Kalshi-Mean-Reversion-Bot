export function formatCents(cents: number | null | undefined): string {
  if (cents == null) return "--";
  const dollars = cents / 100;
  return dollars.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

export function formatPnl(cents: number | null | undefined): string {
  if (cents == null) return "--";
  const str = formatCents(Math.abs(cents));
  if (cents > 0) return `+${str}`;
  if (cents < 0) return `-${str}`;
  return str;
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "--";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function isLiveStatus(status: string | null | undefined): boolean {
  const normalized = String(status ?? "").toLowerCase();
  return normalized.includes("in_progress") || normalized.includes("end_period") || normalized === "live";
}

export function isFinalStatus(status: string | null | undefined): boolean {
  const normalized = String(status ?? "").toLowerCase();
  return normalized.includes("final") || normalized.includes("full_time") || normalized === "post";
}

export function sortGamesByPriority<T extends { start_time: string; status: string }>(
  games: T[],
): T[] {
  return [...games].sort((a, b) => {
    const aLive = isLiveStatus(a.status) ? 0 : 1;
    const bLive = isLiveStatus(b.status) ? 0 : 1;
    if (aLive !== bLive) return aLive - bLive;
    return new Date(a.start_time).getTime() - new Date(b.start_time).getTime();
  });
}

export function pnlColor(cents: number | null | undefined): string {
  if (cents == null || cents === 0) return "text-zinc-400";
  return cents > 0 ? "text-profit" : "text-loss";
}

export function statusBadgeClass(status: string): string {
  switch (status) {
    case "open":
      return "bg-accent/20 text-accent-light";
    case "resolved_win":
      return "bg-profit/20 text-profit";
    case "resolved_loss":
      return "bg-loss/20 text-loss";
    case "expired":
      return "bg-zinc-700/40 text-zinc-400";
    default:
      return "bg-zinc-700/40 text-zinc-400";
  }
}

const PLATFORM_TIME_ZONE = "America/New_York";
const PLATFORM_TIME_LABEL = "ET";

function formatInPlatformTimeZone(
  iso: string | number | Date,
  options: Intl.DateTimeFormatOptions,
): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: PLATFORM_TIME_ZONE,
    ...options,
  }).format(new Date(iso));
}

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

export function formatLine(value: number | null | undefined): string {
  if (value == null) return "--";
  if (value > 0) return `+${value.toFixed(1)}`;
  return value.toFixed(1);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "--";
  return `${formatInPlatformTimeZone(iso, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })} ${PLATFORM_TIME_LABEL}`;
}

export function formatTime(iso: string | number | Date | null | undefined): string {
  if (iso == null) return "--";
  return `${formatInPlatformTimeZone(iso, {
    hour: "numeric",
    minute: "2-digit",
  })} ${PLATFORM_TIME_LABEL}`;
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "--";
  const diffMs = new Date(iso).getTime() - Date.now();
  const absMins = Math.floor(Math.abs(diffMs) / 60_000);

  if (absMins < 1) return "now";
  if (diffMs > 0) {
    if (absMins < 60) return `in ${absMins}m`;
    const hours = Math.floor(absMins / 60);
    if (hours < 24) return `in ${hours}h`;
    return `in ${Math.floor(hours / 24)}d`;
  }

  if (absMins < 60) return `${absMins}m ago`;
  const hours = Math.floor(absMins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function platformTimeLabel(): string {
  return PLATFORM_TIME_LABEL;
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
    case "resolved_push":
      return "bg-surface-3 text-text-dim";
    case "expired":
      return "bg-zinc-700/40 text-zinc-400";
    default:
      return "bg-zinc-700/40 text-zinc-400";
  }
}

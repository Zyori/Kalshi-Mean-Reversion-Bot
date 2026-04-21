const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    ...init,
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface HealthStatus {
  status: string;
  uptime_seconds: number;
  sources: Record<string, string>;
}

export interface Game {
  id: number;
  sport: string;
  home_team: string;
  away_team: string;
  start_time: string;
  espn_id: string | null;
  status: string;
  opening_line_home_prob: number | null;
  opening_line_source: string | null;
}

export interface GameEvent {
  id: number;
  game_id: number;
  event_type: string;
  description: string | null;
  home_score: number | null;
  away_score: number | null;
  period: string | null;
  clock: string | null;
  detected_at: string;
  classification: string | null;
  confidence_score: number | null;
  kalshi_price_at: number | null;
  baseline_prob: number | null;
  deviation: number | null;
}

export interface Trade {
  id: number;
  game_event_id: number | null;
  market_id: number | null;
  sport: string;
  side: string;
  entry_price: number;
  entry_price_adj: number;
  slippage_cents: number;
  confidence_score: number;
  kelly_fraction: number;
  kelly_size_cents: number;
  exit_price: number | null;
  pnl_cents: number | null;
  pnl_kelly_cents: number | null;
  status: string;
  entered_at: string;
  resolved_at: string | null;
  game_context: Record<string, unknown> | null;
  reasoning: Record<string, unknown> | null;
  skip_reason: string | null;
}

export interface AnalysisSummary {
  total_trades: number;
  open: number;
  resolved: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl_cents: number;
}

export interface SportBreakdown {
  sport: string;
  count: number;
  total_pnl_cents: number;
}

export interface EventTypeBreakdown {
  event_type: string;
  count: number;
  total_pnl_cents: number;
}

export interface EquityPoint {
  time: string | null;
  pnl: number;
}

export interface KellyPoint {
  kelly: number;
  flat: number;
}

export interface Insight {
  id: number;
  type: string;
  title: string;
  body: string;
  data: Record<string, unknown> | null;
  confidence: number | null;
  recommendation: string | null;
  status: string;
  created_at: string;
}

export interface PublicStatus {
  alive: boolean;
  uptime_seconds: number;
  sources_up: number;
  sources_total: number;
}

export const api = {
  login: (password: string) => post<{ ok: true }>("/auth/login", { password }),
  logout: () => post<{ ok: true }>("/auth/logout"),
  me: () => get<{ authed: true }>("/auth/me"),
  publicStatus: () => get<PublicStatus>("/public/status"),
  publicHeartbeat: () => get<{ ok: true; timestamp: number }>("/public/heartbeat"),
  health: () => get<HealthStatus>("/health"),
  games: (params?: { sport?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.sport) qs.set("sport", params.sport);
    if (params?.status) qs.set("status", params.status);
    const q = qs.toString();
    return get<Game[]>(`/games${q ? `?${q}` : ""}`);
  },
  game: (id: number) => get<Game>(`/games/${id}`),
  gameEvents: (id: number) => get<GameEvent[]>(`/games/${id}/events`),
  events: (params?: {
    sport?: string;
    event_type?: string;
    classification?: string;
    limit?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.sport) qs.set("sport", params.sport);
    if (params?.event_type) qs.set("event_type", params.event_type);
    if (params?.classification) qs.set("classification", params.classification);
    if (params?.limit) qs.set("limit", String(params.limit));
    const q = qs.toString();
    return get<GameEvent[]>(`/events${q ? `?${q}` : ""}`);
  },
  trades: (params?: {
    sport?: string;
    status?: string;
    sort_by?: string;
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.sport) qs.set("sport", params.sport);
    if (params?.status) qs.set("status", params.status);
    if (params?.sort_by) qs.set("sort_by", params.sort_by);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const q = qs.toString();
    return get<Trade[]>(`/trades${q ? `?${q}` : ""}`);
  },
  activeTrades: () => get<Trade[]>("/trades/active"),
  trade: (id: number) => get<Trade>(`/trades/${id}`),
  analysisSummary: () => get<AnalysisSummary>("/analysis/summary"),
  analysisBySport: () => get<SportBreakdown[]>("/analysis/by-sport"),
  analysisByEventType: () =>
    get<EventTypeBreakdown[]>("/analysis/by-event-type"),
  equityCurve: () => get<EquityPoint[]>("/analysis/equity-curve"),
  kellyComparison: () => get<KellyPoint[]>("/analysis/kelly-comparison"),
  insights: (status?: string) => {
    const qs = status ? `?status=${status}` : "";
    return get<Insight[]>(`/insights${qs}`);
  },
  updateConfig: (key: string, value: string, reason?: string) =>
    patch(`/config/${key}`, { value, reason }),
};

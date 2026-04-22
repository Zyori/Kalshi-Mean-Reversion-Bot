import { useMemo, useState } from "react";
import { useGames, useRecentEvents } from "../hooks/useMarkets";
import { useActiveTrades } from "../hooks/useTrades";
import { useAnalysisSummary } from "../hooks/useAnalytics";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import {
  formatDate,
  formatCents,
  formatPercent,
  formatRelative,
  isFinalStatus,
  isLiveStatus,
  platformTimeLabel,
  sortGamesByPriority,
  statusBadgeClass,
} from "../lib/utils";

const SPORTS = ["all", "nhl", "nba", "mlb", "nfl", "soccer", "ufc"] as const;

export function MarketsPage() {
  const [sport, setSport] = useState<string>("all");
  const { data: games, isLoading } = useGames(
    { sport: sport === "all" ? undefined : sport, days_ahead: 7 },
  );
  const { data: recentEvents, isLoading: loadingEvents } = useRecentEvents({
    sport: sport === "all" ? undefined : sport,
    limit: 20,
  });
  const { data: candidateEvents } = useRecentEvents({
    sport: sport === "all" ? undefined : sport,
    classification: "reversion_candidate",
    limit: 10,
  });
  const { data: activeTrades } = useActiveTrades();
  const { data: summary } = useAnalysisSummary();
  const sortedRecentEvents = [...(recentEvents ?? [])].sort(
    (a, b) =>
      new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime(),
  );
  const prioritizedGames = useMemo(
    () => sortGamesByPriority((games ?? []).filter((game) => !isFinalStatus(game.status))),
    [games],
  );
  const liveGames = useMemo(
    () => prioritizedGames.filter((game) => isLiveStatus(game.status)).slice(0, 6),
    [prioritizedGames],
  );
  const now = Date.now();
  const next24Hours = useMemo(
    () =>
      prioritizedGames
        .filter((game) => {
          if (isLiveStatus(game.status)) return false;
          const start = new Date(game.start_time).getTime();
          return start >= now && start <= now + 24 * 60 * 60 * 1000;
        })
        .slice(0, 8),
    [now, prioritizedGames],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Live Markets</h2>
          <p className="text-sm text-text-dim">All game starts and timestamps shown in {platformTimeLabel()}.</p>
        </div>
        <div className="flex gap-1">
          {SPORTS.map((s) => (
            <button
              key={s}
              onClick={() => setSport(s)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium uppercase transition-colors ${
                sport === s
                  ? "bg-accent/15 text-accent-light"
                  : "text-text-dim hover:text-text hover:bg-surface-2"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <Card className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-text-dim">Live Now</p>
          <p className="font-mono text-lg">{liveGames.length}</p>
        </Card>
        <Card className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-text-dim">Next 24h</p>
          <p className="font-mono text-lg">{next24Hours.length}</p>
        </Card>
        <Card className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-text-dim">Candidates</p>
          <p className="font-mono text-lg">{candidateEvents?.length ?? 0}</p>
          <p className="text-xs text-text-dim">Recent reversion triggers</p>
        </Card>
        <Card className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-text-dim">Mock Bank</p>
          <p className="font-mono text-lg">
            {summary ? formatCents(summary.current_bankroll_cents) : "--"}
          </p>
        </Card>
      </div>

      {activeTrades && activeTrades.length > 0 && (
        <Card>
          <h3 className="mb-3 text-sm font-medium text-text-dim">
            Open Positions ({activeTrades.length})
          </h3>
          <div className="space-y-2">
            {activeTrades.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between rounded-md bg-surface-2 px-3 py-2 text-sm"
              >
                <div className="flex items-center gap-3">
                  <Badge className="bg-accent/20 text-accent-light uppercase">
                    {t.sport}
                  </Badge>
                  <Badge className="bg-surface-3 text-text-dim uppercase text-[10px]">
                    {t.market_category}
                  </Badge>
                  <span className="text-sm">{t.selected_team ?? t.side}</span>
                  <span className="font-mono tabular-nums">{t.entry_price}c</span>
                  {t.matchup && (
                    <span className="text-text-dim">{t.matchup}</span>
                  )}
                </div>
                <span className="text-xs text-text-dim">
                  {formatDate(t.entered_at)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-medium text-text-dim">Live Now</h3>
            <span className="text-xs text-text-dim">Best watchlist</span>
          </div>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-20" />
              ))}
            </div>
          ) : liveGames.length === 0 ? (
            <p className="py-6 text-center text-sm text-text-dim">No live games right now</p>
          ) : (
            <div className="space-y-2">
              {liveGames.map((game) => (
                <div key={game.id} className="rounded-md bg-surface-2 px-3 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge className="bg-accent/20 text-accent-light uppercase text-[10px]">
                        {game.sport}
                      </Badge>
                      <Badge className={statusBadgeClass(game.status)}>{game.status}</Badge>
                    </div>
                    <span className="text-xs text-text-dim">{formatDate(game.start_time)}</span>
                  </div>
                  <p className="mt-2 text-sm font-medium">
                    {game.away_team} @ {game.home_team}
                  </p>
                  <div className="mt-1 flex items-center justify-between text-xs text-text-dim">
                    <span>
                      Score {game.away_team} {game.latest_away_score ?? "-"} -{" "}
                      {game.latest_home_score ?? "-"} {game.home_team}
                    </span>
                    <span>
                      {game.opening_line_home_prob != null
                        ? `Home ${formatPercent(game.opening_line_home_prob)}`
                        : "Home --"}
                      {game.opening_total != null ? ` • Total ${game.opening_total.toFixed(1)}` : ""}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-medium text-text-dim">Upcoming 24 Hours</h3>
            <span className="text-xs text-text-dim">Soonest first</span>
          </div>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : next24Hours.length === 0 ? (
            <p className="py-6 text-center text-sm text-text-dim">
              No tracked games in the next 24 hours
            </p>
          ) : (
            <div className="space-y-2">
              {next24Hours.map((game) => (
                <div key={game.id} className="rounded-md bg-surface-2 px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge className="bg-surface-3 text-text-dim uppercase text-[10px]">
                        {game.sport}
                      </Badge>
                      <span className="text-sm font-medium">
                        {game.away_team} @ {game.home_team}
                      </span>
                    </div>
                    <span className="text-xs text-text-dim">{formatRelative(game.start_time)}</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-xs text-text-dim">
                    <span>{formatDate(game.start_time)}</span>
                    <span>
                      {game.opening_line_home_prob != null
                        ? `Home ${formatPercent(game.opening_line_home_prob)}`
                        : "Home --"}
                      {game.opening_total != null ? ` • Total ${game.opening_total.toFixed(1)}` : ""}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-medium text-text-dim">Recent Key Events</h3>
          <span className="text-xs text-text-dim">Newest first</span>
        </div>
        {loadingEvents ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : sortedRecentEvents.length === 0 ? (
          <p className="py-6 text-center text-sm text-text-dim">
            No key events captured yet
          </p>
        ) : (
          <div className="space-y-2">
            {sortedRecentEvents.map((event) => (
              <div
                key={event.id}
                className="rounded-md bg-surface-2 px-3 py-2"
              >
                <div className="mb-1 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-surface-3 text-text-dim uppercase text-[10px]">
                      {event.sport ?? "event"}
                    </Badge>
                    {event.market_category && (
                      <Badge className="bg-accent/10 text-accent-light uppercase text-[10px]">
                        {event.market_category}
                      </Badge>
                    )}
                    <span className="text-sm font-medium">{event.event_type}</span>
                  </div>
                  <span className="text-xs text-text-dim">
                    {formatRelative(event.detected_at)}
                  </span>
                </div>
                {event.description && (
                  <p className="text-sm text-text">
                    {event.description}
                  </p>
                )}
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-text-dim">
                  {event.home_team && event.away_team && (
                    <span>
                      {event.away_team} @ {event.home_team}
                    </span>
                  )}
                  <span>
                    Score {event.away_score ?? "-"}-{event.home_score ?? "-"}
                  </span>
                  {event.classification && <span>{event.classification}</span>}
                  {event.kalshi_price_at != null && (
                    <span>Kalshi {formatCents(event.kalshi_price_at)}</span>
                  )}
                  {event.baseline_prob != null && (
                    <span>Base {formatPercent(event.baseline_prob)}</span>
                  )}
                  {event.deviation != null && (
                    <span>Dev {formatPercent(event.deviation)}</span>
                  )}
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-text-dim">
                  <span>
                    {event.period ? `P${event.period}` : "--"}
                    {event.clock ? ` • ${event.clock}` : ""}
                  </span>
                  <span>{formatDate(event.detected_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : prioritizedGames.length === 0 ? (
        <Card>
          <p className="text-center text-sm text-text-dim py-8">
            No games found
          </p>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {prioritizedGames.slice(0, 12).map((g) => (
            <Card key={g.id} className="space-y-2">
              <div className="flex items-center justify-between">
                <Badge className="bg-surface-2 text-text-dim uppercase text-[10px]">
                  {g.sport}
                </Badge>
                <Badge className={statusBadgeClass(g.status)}>
                  {g.status}
                </Badge>
              </div>
              <p className="text-sm font-medium">
                {g.away_team} @ {g.home_team}
              </p>
              <div className="flex items-center justify-between text-xs text-text-dim">
                <span>{formatDate(g.start_time)}</span>
                <span className="font-mono tabular-nums">
                  {g.opening_line_home_prob != null
                    ? `Home ${formatPercent(g.opening_line_home_prob)}`
                    : "Home --"}
                  {g.opening_total != null ? ` • Tot ${g.opening_total.toFixed(1)}` : ""}
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
import { useGames } from "../hooks/useMarkets";
import { useActiveTrades } from "../hooks/useTrades";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { formatDate, formatPercent, statusBadgeClass } from "../lib/utils";

const SPORTS = ["all", "nhl", "nba", "mlb", "nfl", "soccer", "ufc"] as const;

export function MarketsPage() {
  const [sport, setSport] = useState<string>("all");
  const { data: games, isLoading } = useGames(
    sport === "all" ? undefined : sport,
  );
  const { data: activeTrades } = useActiveTrades();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Live Markets</h2>
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
                  <span className="font-mono tabular-nums">
                    {t.entry_price}c
                  </span>
                  <span className="text-text-dim">{t.side}</span>
                </div>
                <span className="text-xs text-text-dim">
                  {formatDate(t.entered_at)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : !games || games.length === 0 ? (
        <Card>
          <p className="text-center text-sm text-text-dim py-8">
            No games found
          </p>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {games.map((g) => (
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
                {g.opening_line_home_prob != null && (
                  <span className="font-mono tabular-nums">
                    Home {formatPercent(g.opening_line_home_prob)}
                  </span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

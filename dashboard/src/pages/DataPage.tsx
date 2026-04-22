import { useEffect, useMemo, useState } from "react";
import { useGame, useGames } from "../hooks/useMarkets";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import {
  formatDate,
  formatPercent,
  formatRelative,
  isFinalStatus,
  platformTimeLabel,
  sortGamesByPriority,
  statusBadgeClass,
} from "../lib/utils";

const SPORTS = ["all", "nhl", "nba", "mlb", "nfl", "soccer", "ufc"] as const;

export function DataPage() {
  const [sport, setSport] = useState<string>("all");
  const { data: games, isLoading } = useGames({
    sport: sport === "all" ? undefined : sport,
    days_ahead: 7,
  });
  const [selectedGameId, setSelectedGameId] = useState<number | null>(null);

  useEffect(() => {
    if (!games || games.length === 0) {
      setSelectedGameId(null);
      return;
    }
    setSelectedGameId((current) =>
      current && games.some((game) => game.id === current) ? current : games[0].id,
    );
  }, [games]);

  const { data: selectedGame, isLoading: loadingGame } = useGame(selectedGameId ?? 0);

  const collectedGames = useMemo(
    () =>
      sortGamesByPriority(
        (games ?? []).filter(
          (game) =>
            !isFinalStatus(game.status) &&
            (game.opening_line_home_prob != null || game.espn_id),
        ),
      ),
    [games],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Data Feed</h2>
          <p className="text-sm text-text-dim">
            Raw collection view for games, opening lines, and captured event flow in {platformTimeLabel()}.
          </p>
        </div>
        <div className="flex gap-1">
          {SPORTS.map((entry) => (
            <button
              key={entry}
              onClick={() => setSport(entry)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium uppercase transition-colors ${
                sport === entry
                  ? "bg-accent/15 text-accent-light"
                  : "text-text-dim hover:text-text hover:bg-surface-2"
              }`}
            >
              {entry}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-text-dim">Collected Games</h3>
            <span className="text-xs text-text-dim">{collectedGames.length} tracked</span>
          </div>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, index) => (
                <Skeleton key={index} className="h-20" />
              ))}
            </div>
          ) : collectedGames.length === 0 ? (
            <p className="py-8 text-center text-sm text-text-dim">
              No collected games in this filter yet
            </p>
          ) : (
            <div className="space-y-2">
              {collectedGames.map((game) => {
                const selected = game.id === selectedGameId;
                return (
                  <button
                    key={game.id}
                    type="button"
                    onClick={() => setSelectedGameId(game.id)}
                    className={`w-full rounded-lg border px-3 py-3 text-left transition-colors ${
                      selected
                        ? "border-accent/40 bg-accent/10"
                        : "border-border bg-surface-2 hover:bg-surface-3"
                    }`}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <Badge className="bg-surface-3 text-text-dim uppercase text-[10px]">
                        {game.sport}
                      </Badge>
                      <Badge className={statusBadgeClass(game.status)}>{game.status}</Badge>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-medium">
                        {game.away_team} @ {game.home_team}
                      </p>
                      <div className="flex items-center justify-between text-xs text-text-dim">
                        <span>{formatDate(game.start_time)}</span>
                        {game.opening_line_home_prob != null && (
                          <span>Home {formatPercent(game.opening_line_home_prob)}</span>
                        )}
                      </div>
                      {(game.latest_home_score != null || game.latest_away_score != null) && (
                        <div className="text-xs text-text-dim">
                          Score {game.away_team} {game.latest_away_score ?? "-"} -{" "}
                          {game.latest_home_score ?? "-"} {game.home_team}
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </Card>

        <div className="space-y-4">
          {loadingGame || !selectedGameId ? (
            <Card>
              <Skeleton className="h-64" />
            </Card>
          ) : !selectedGame ? (
            <Card>
              <p className="py-10 text-center text-sm text-text-dim">Select a tracked game</p>
            </Card>
          ) : (
            <>
              <Card className="space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge className="bg-surface-2 text-text-dim uppercase text-[10px]">
                        {selectedGame.sport}
                      </Badge>
                      <Badge className={statusBadgeClass(selectedGame.status)}>
                        {selectedGame.status}
                      </Badge>
                    </div>
                    <h3 className="text-lg font-semibold">
                      {selectedGame.away_team} @ {selectedGame.home_team}
                    </h3>
                    <p className="text-sm text-text-dim">
                      ESPN {selectedGame.espn_id ?? "pending"} • {formatDate(selectedGame.start_time)}
                    </p>
                  </div>
                  <div className="grid gap-2 text-right text-sm">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-text-dim">Score</div>
                      <div>
                        {selectedGame.away_team} {selectedGame.latest_away_score ?? "-"} |{" "}
                        {selectedGame.home_team} {selectedGame.latest_home_score ?? "-"}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-text-dim">
                        Opening Line
                      </div>
                      <div>
                        {selectedGame.opening_line_home_prob != null
                          ? `Home ${formatPercent(selectedGame.opening_line_home_prob)}`
                          : "--"}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-lg bg-surface-2 p-3">
                    <div className="text-xs uppercase tracking-wide text-text-dim">
                      Event Count
                    </div>
                    <div className="mt-1 text-xl font-semibold">{selectedGame.events.length}</div>
                  </div>
                  <div className="rounded-lg bg-surface-2 p-3">
                    <div className="text-xs uppercase tracking-wide text-text-dim">
                      Opening Snapshots
                    </div>
                    <div className="mt-1 text-xl font-semibold">
                      {selectedGame.opening_lines.length}
                    </div>
                  </div>
                  <div className="rounded-lg bg-surface-2 p-3">
                    <div className="text-xs uppercase tracking-wide text-text-dim">
                      Last Capture
                    </div>
                    <div className="mt-1 text-sm font-medium">
                      {selectedGame.events[0]?.detected_at
                        ? formatRelative(selectedGame.events[0].detected_at)
                        : "--"}
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-text-dim">Opening Line History</h4>
                    {selectedGame.opening_lines.length === 0 ? (
                      <div className="rounded-lg bg-surface-2 p-3 text-sm text-text-dim">
                        No line snapshots recorded yet
                      </div>
                    ) : (
                      selectedGame.opening_lines.map((line) => (
                        <div key={line.id} className="rounded-lg bg-surface-2 p-3 text-sm">
                          <div className="flex items-center justify-between gap-2">
                            <span className="uppercase text-[10px] text-text-dim">
                              {line.source}
                            </span>
                            <span className="text-xs text-text-dim">
                              {formatDate(line.captured_at)}
                            </span>
                          </div>
                          <div className="mt-2 text-text-dim">
                            Home {formatPercent(line.home_prob)} • Away {formatPercent(line.away_prob)}
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-text-dim">Captured Events</h4>
                    {selectedGame.events.length === 0 ? (
                      <div className="rounded-lg bg-surface-2 p-3 text-sm text-text-dim">
                        No events captured for this game yet
                      </div>
                    ) : (
                      selectedGame.events.map((event) => (
                        <div key={event.id} className="rounded-lg bg-surface-2 p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <Badge className="bg-surface-3 text-text-dim uppercase text-[10px]">
                                {event.event_type}
                              </Badge>
                              {event.classification && (
                                <Badge className="bg-accent/15 text-accent-light">
                                  {event.classification}
                                </Badge>
                              )}
                            </div>
                            <span className="text-xs text-text-dim">
                              {formatDate(event.detected_at)}
                            </span>
                          </div>
                          {event.description && (
                            <p className="mt-2 text-sm">{event.description}</p>
                          )}
                          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-text-dim">
                            <span>
                              Score {event.away_score ?? "-"}-{event.home_score ?? "-"}
                            </span>
                            <span>
                              {event.period ? `P${event.period}` : "--"}
                              {event.clock ? ` • ${event.clock}` : ""}
                            </span>
                            {event.kalshi_price_at != null && (
                              <span>Kalshi {event.kalshi_price_at}c</span>
                            )}
                            {event.baseline_prob != null && (
                              <span>Base {formatPercent(event.baseline_prob)}</span>
                            )}
                            {event.deviation != null && (
                              <span>Dev {formatPercent(event.deviation)}</span>
                            )}
                          </div>
                          {event.espn_data && (
                            <details className="mt-3 rounded-md bg-surface-1 p-2">
                              <summary className="cursor-pointer text-xs text-text-dim">
                                Raw ESPN payload
                              </summary>
                              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-text-dim">
                                {JSON.stringify(event.espn_data, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

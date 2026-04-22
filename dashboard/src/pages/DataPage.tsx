import { useEffect, useMemo, useState } from "react";
import { useGame, useGames } from "../hooks/useMarkets";
import type { GameEvent } from "../lib/api";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import {
  formatDate,
  formatLine,
  formatPercent,
  formatRelative,
  isLiveStatus,
  isFinalStatus,
  platformTimeLabel,
  sortGamesByPriority,
  statusBadgeClass,
} from "../lib/utils";

const SPORTS = ["all", "nhl", "nba", "mlb", "nfl", "soccer", "ufc"] as const;

function buildEventFeed(events: GameEvent[]) {
  const grouped = new Map<
    string,
    {
      event: GameEvent;
      marketCategories: string[];
      classifications: string[];
    }
  >();

  for (const event of events) {
    const key = [
      event.detected_at,
      event.event_type,
      event.description ?? "",
      event.home_score ?? "",
      event.away_score ?? "",
      event.period ?? "",
      event.clock ?? "",
    ].join("|");

    const existing = grouped.get(key);
    if (!existing) {
      grouped.set(key, {
        event,
        marketCategories: event.market_category ? [event.market_category] : [],
        classifications: event.classification ? [event.classification] : [],
      });
      continue;
    }

    if (event.market_category && !existing.marketCategories.includes(event.market_category)) {
      existing.marketCategories.push(event.market_category);
    }
    if (event.classification && !existing.classifications.includes(event.classification)) {
      existing.classifications.push(event.classification);
    }
  }

  return Array.from(grouped.values());
}

export function DataPage() {
  const [sport, setSport] = useState<string>("all");
  const { data: activeGames, isLoading: loadingActiveGames } = useGames({
    sport: sport === "all" ? undefined : sport,
    days_ahead: 7,
    sort: "asc",
    limit: 80,
  });
  const { data: historyGames, isLoading: loadingHistoryGames } = useGames({
    sport: sport === "all" ? undefined : sport,
    days_back: 30,
    sort: "desc",
    limit: 120,
  });
  const [selectedGameId, setSelectedGameId] = useState<number | null>(null);

  useEffect(() => {
    const availableGames = [...(activeGames ?? []), ...(historyGames ?? [])];
    if (availableGames.length === 0) {
      setSelectedGameId(null);
      return;
    }
    setSelectedGameId((current) =>
      current && availableGames.some((game) => game.id === current)
        ? current
        : availableGames[0].id,
    );
  }, [activeGames, historyGames]);

  const { data: selectedGame, isLoading: loadingGame } = useGame(selectedGameId ?? 0);
  const selectedGameHasLiveFeed = Boolean(
    selectedGame && (isLiveStatus(selectedGame.status) || isFinalStatus(selectedGame.status)),
  );
  const selectedEventFeed = useMemo(
    () => (selectedGameHasLiveFeed ? buildEventFeed(selectedGame?.events ?? []) : []),
    [selectedGame, selectedGameHasLiveFeed],
  );

  const trackedActiveGames = useMemo(
    () =>
      sortGamesByPriority(
        (activeGames ?? []).filter(
          (game) =>
            !isFinalStatus(game.status) &&
            (game.opening_line_home_prob != null || game.espn_id),
        ),
      ),
    [activeGames],
  );

  const historicalGames = useMemo(
    () =>
      (historyGames ?? []).filter(
        (game) =>
          isFinalStatus(game.status) &&
          (game.opening_line_home_prob != null || game.espn_id),
      ),
    [historyGames],
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
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-text-dim">Live + Upcoming</h3>
              <span className="text-xs text-text-dim">{trackedActiveGames.length} tracked</span>
            </div>
            {loadingActiveGames ? (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Skeleton key={index} className="h-20" />
                ))}
              </div>
            ) : trackedActiveGames.length === 0 ? (
              <p className="py-4 text-center text-sm text-text-dim">
                No live or upcoming tracked games in this filter
              </p>
            ) : (
              <div className="space-y-2">
                {trackedActiveGames.map((game) => {
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
                          !isFinalStatus(game.status) && !isLiveStatus(game.status) ? null : (
                          <div className="text-xs text-text-dim">
                            Score {game.away_team} {game.latest_away_score ?? "-"} -{" "}
                            {game.latest_home_score ?? "-"} {game.home_team}
                          </div>
                          )
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
          <div className="mt-4 border-t border-border pt-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-medium text-text-dim">Historical Collection</h3>
              <span className="text-xs text-text-dim">{historicalGames.length} final games</span>
            </div>
            {loadingHistoryGames ? (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Skeleton key={index} className="h-16" />
                ))}
              </div>
            ) : historicalGames.length === 0 ? (
              <p className="py-4 text-center text-sm text-text-dim">
                No recent historical tracked games yet
              </p>
            ) : (
              <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
                {historicalGames.map((game) => {
                  const selected = game.id === selectedGameId;
                  return (
                    <button
                      key={game.id}
                      type="button"
                      onClick={() => setSelectedGameId(game.id)}
                      className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                        selected
                          ? "border-accent/40 bg-accent/10"
                          : "border-border bg-surface-2 hover:bg-surface-3"
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <Badge className="bg-surface-3 text-text-dim uppercase text-[10px]">
                          {game.sport}
                        </Badge>
                        <Badge className={statusBadgeClass(game.status)}>{game.status}</Badge>
                      </div>
                      <p className="text-sm font-medium">
                        {game.away_team} @ {game.home_team}
                      </p>
                      <div className="mt-1 flex items-center justify-between text-xs text-text-dim">
                        <span>{formatDate(game.start_time)}</span>
                        <span>
                          {game.away_team} {game.final_away_score ?? "-"} -{" "}
                          {game.final_home_score ?? "-"} {game.home_team}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
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
                      <div className="text-xs text-text-dim">
                        {selectedGame.opening_spread_home != null
                          ? `Spread ${formatLine(selectedGame.opening_spread_home)}`
                          : "Spread --"}
                        {" • "}
                        {selectedGame.opening_total != null
                          ? `Total ${selectedGame.opening_total.toFixed(1)}`
                          : "Total --"}
                      </div>
                      <div className="text-xs text-text-dim">
                        {selectedGame.opening_home_team_total != null
                          ? `${selectedGame.home_team} TT ${selectedGame.opening_home_team_total.toFixed(1)}`
                          : `${selectedGame.home_team} TT --`}
                        {" • "}
                        {selectedGame.opening_away_team_total != null
                          ? `${selectedGame.away_team} TT ${selectedGame.opening_away_team_total.toFixed(1)}`
                          : `${selectedGame.away_team} TT --`}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-lg bg-surface-2 p-3">
                      <div className="text-xs uppercase tracking-wide text-text-dim">
                        Event Count
                      </div>
                      <div className="mt-1 text-xl font-semibold">{selectedEventFeed.length}</div>
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
                      {selectedEventFeed[0]?.event.detected_at
                        ? formatRelative(selectedEventFeed[0].event.detected_at)
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
                          <div className="mt-1 text-xs text-text-dim">
                            Spread {formatLine(line.home_spread)} / {formatLine(line.away_spread)}
                          </div>
                          <div className="mt-1 text-xs text-text-dim">
                            Total {line.total_points?.toFixed(1) ?? "--"} • {selectedGame.home_team} TT{" "}
                            {line.home_team_total?.toFixed(1) ?? "--"} • {selectedGame.away_team} TT{" "}
                            {line.away_team_total?.toFixed(1) ?? "--"}
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-text-dim">Captured Events</h4>
                    {!selectedGameHasLiveFeed ? (
                      <div className="rounded-lg bg-surface-2 p-3 text-sm text-text-dim">
                        Live capture begins once the game is in progress.
                      </div>
                    ) : selectedEventFeed.length === 0 ? (
                      <div className="rounded-lg bg-surface-2 p-3 text-sm text-text-dim">
                        No events captured for this game yet
                      </div>
                    ) : (
                      selectedEventFeed.map(({ event, marketCategories, classifications }) => (
                        <div key={event.id} className="rounded-lg bg-surface-2 p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <Badge className="bg-surface-3 text-text-dim uppercase text-[10px]">
                                {event.event_type}
                              </Badge>
                              {marketCategories.map((category) => (
                                <Badge
                                  key={`${event.id}-${category}`}
                                  className="bg-surface-3 text-text-dim uppercase text-[10px]"
                                >
                                  {category}
                                </Badge>
                              ))}
                              {classifications.map((classification) => (
                                <Badge
                                  key={`${event.id}-${classification}`}
                                  className="bg-accent/15 text-accent-light"
                                >
                                  {classification}
                                </Badge>
                              ))}
                            </div>
                            <span className="text-xs text-text-dim">
                              {formatDate(event.detected_at)}
                            </span>
                          </div>
                          {(event.market_label_yes || event.market_label_no) && (
                            <div className="mt-1 text-xs text-text-dim">
                              {event.market_label_yes ?? "--"} / {event.market_label_no ?? "--"}
                            </div>
                          )}
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

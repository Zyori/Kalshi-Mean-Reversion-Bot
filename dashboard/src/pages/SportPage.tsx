import { useMemo, useState } from "react";
import { useParams, Link } from "react-router";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useGames } from "../hooks/useMarkets";
import { useRecentEvents } from "../hooks/useMarkets";
import { useTrades } from "../hooks/useTrades";
import { useSports } from "../hooks/useSports";
import { useFindings, useCreateFinding } from "../hooks/useFindings";
import {
  isFinalStatus,
  isLiveStatus,
  formatRelative,
  formatTime,
  sortGamesByPriority,
} from "../lib/utils";
import {
  sportDisplayName,
  sportModeBadgeClass,
  sportModeLabel,
} from "../lib/sports";
import type { Game, GameEvent, Insight, Trade } from "../lib/api";

/**
 * Sport-Overview page. The primary surface for a single sport: mode + intent,
 * live games right now, upcoming today, recently completed, recent events,
 * and open paper positions. Designed so a glance answers "what's the bot
 * doing for this sport right now?"
 */
export function SportPage() {
  const { sport = "" } = useParams<{ sport: string }>();
  const { data: sports } = useSports();
  const entry = sports?.find((s) => s.sport === sport);

  const { data: games } = useGames({ sport, days_ahead: 7, days_back: 1, limit: 200 });
  const { data: events } = useRecentEvents({ sport, limit: 15 });
  const { data: openTrades } = useTrades({ sport, status: "open", limit: 20 });

  const partitioned = useMemo(() => partitionGames(games ?? []), [games]);

  if (sports && !entry) {
    return (
      <div className="text-text-dim">
        Unknown sport: <span className="font-mono">{sport}</span>.{" "}
        <Link to="/" className="text-accent-light underline-offset-2 hover:underline">
          Back to overview
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            {sportDisplayName(sport)}
          </h2>
          {entry && (
            <Badge className={sportModeBadgeClass(entry.mode)}>
              {sportModeLabel(entry.mode)}
            </Badge>
          )}
        </div>
        <div className="text-xs text-text-dim">
          {games?.length ?? 0} games tracked · {events?.length ?? 0} recent events ·{" "}
          {openTrades?.length ?? 0} open positions
        </div>
      </header>

      {entry?.notes && (
        <Card className="bg-surface-2/50 text-sm text-text-dim">{entry.notes}</Card>
      )}

      {entry?.mode === "passive" && (
        <Card className="border-accent/30 bg-accent/5 text-sm text-text-dim">
          This sport is in <span className="font-medium text-accent-light">passive</span>{" "}
          mode — schedules and opening lines are collected, but no live events
          are polled and no paper trades are placed. Flip to active in the
          sport config when you want it to engage.
        </Card>
      )}

      <section className="grid gap-4 md:grid-cols-2">
        <GameList title="Live now" games={partitioned.live} emptyText="No games in progress." />
        <GameList title="Up next" games={partitioned.upcoming} emptyText="No upcoming games." />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-text">Recent events</h3>
          <EventList events={events ?? []} />
        </Card>
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-text">Open paper positions</h3>
          <TradeList trades={openTrades ?? []} />
        </Card>
      </section>

      <section>
        <FindingsSection sport={sport} />
      </section>

      {partitioned.recentFinal.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-text">Recently completed</h3>
          <GameList title="" games={partitioned.recentFinal} emptyText="" />
        </section>
      )}
    </div>
  );
}

function partitionGames(games: Game[]) {
  const live: Game[] = [];
  const upcoming: Game[] = [];
  const recentFinal: Game[] = [];
  for (const g of games) {
    if (isLiveStatus(g.status)) live.push(g);
    else if (isFinalStatus(g.status)) recentFinal.push(g);
    else upcoming.push(g);
  }
  return {
    live: sortGamesByPriority(live),
    upcoming: sortGamesByPriority(upcoming).slice(0, 12),
    recentFinal: recentFinal
      .sort(
        (a, b) =>
          new Date(b.start_time).getTime() - new Date(a.start_time).getTime(),
      )
      .slice(0, 8),
  };
}

function GameList({
  title,
  games,
  emptyText,
}: {
  title: string;
  games: Game[];
  emptyText: string;
}) {
  const body =
    games.length === 0 ? (
      <p className="text-sm text-text-dim">{emptyText}</p>
    ) : (
      <ul className="space-y-2">
        {games.map((g) => (
          <li key={g.id}>
            <GameRow game={g} />
          </li>
        ))}
      </ul>
    );
  if (!title) return body;
  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-text">{title}</h3>
      {body}
    </Card>
  );
}

function GameRow({ game }: { game: Game }) {
  const live = isLiveStatus(game.status);
  const final = isFinalStatus(game.status);
  return (
    <div className="flex items-center justify-between rounded-md border border-border/60 bg-surface-2/40 px-3 py-2">
      <div className="min-w-0">
        <div className="truncate text-sm text-text">
          {game.home_team} <span className="text-text-dim">vs</span> {game.away_team}
        </div>
        <div className="mt-0.5 text-xs text-text-dim">
          {live
            ? `Live · ${game.status.replace(/^STATUS_/, "").replaceAll("_", " ").toLowerCase()}`
            : final
              ? "Final"
              : formatTime(game.start_time)}
        </div>
      </div>
      <div className="shrink-0 text-right">
        {live || final ? (
          <ScoreReadout
            home={game.latest_home_score ?? game.final_home_score}
            away={game.latest_away_score ?? game.final_away_score}
          />
        ) : (
          <span className="text-xs text-text-dim">
            {formatRelative(game.start_time)}
          </span>
        )}
      </div>
    </div>
  );
}

function ScoreReadout({
  home,
  away,
}: {
  home: number | null;
  away: number | null;
}) {
  return (
    <span className="font-mono text-sm text-text">
      {home ?? "-"} <span className="text-text-dim">–</span> {away ?? "-"}
    </span>
  );
}

function EventList({ events }: { events: GameEvent[] }) {
  if (events.length === 0)
    return <p className="text-sm text-text-dim">No events captured yet.</p>;
  return (
    <ul className="space-y-2">
      {events.slice(0, 10).map((e) => (
        <li
          key={e.id}
          className="flex items-start justify-between gap-3 rounded-md border border-border/60 bg-surface-2/40 px-3 py-2"
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-text">{e.event_type}</span>
              {e.clock && (
                <span className="font-mono text-xs text-text-dim">{e.clock}</span>
              )}
            </div>
            <div className="mt-0.5 line-clamp-2 text-xs text-text-dim">
              {e.description ?? ""}
            </div>
          </div>
          <span className="shrink-0 text-xs text-text-dim">
            {formatRelative(e.detected_at)}
          </span>
        </li>
      ))}
    </ul>
  );
}

function FindingsSection({ sport }: { sport: string }) {
  const { data: findings, isLoading } = useFindings(sport);
  const create = useCreateFinding();
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [recommendation, setRecommendation] = useState("");

  function reset() {
    setTitle("");
    setBody("");
    setRecommendation("");
    setAdding(false);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;
    create.mutate(
      {
        sport,
        title: title.trim(),
        body: body.trim(),
        recommendation: recommendation.trim() || null,
      },
      { onSuccess: reset },
    );
  }

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text">Findings</h3>
          <p className="mt-0.5 text-xs text-text-dim">
            What we've learned about{" "}
            <span className="text-text">{sportDisplayName(sport)}</span> as the
            bot watches and trades. Auto-generated insights and operator notes
            share one timeline.
          </p>
        </div>
        {!adding && (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-text-dim transition-colors hover:border-accent/40 hover:text-text"
          >
            + Add finding
          </button>
        )}
      </div>

      {adding && (
        <form
          onSubmit={submit}
          className="mb-4 space-y-2 rounded-md border border-accent/30 bg-accent/5 p-3"
        >
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Headline (e.g. 'Late-game goals overshoot')"
            maxLength={200}
            className="w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-sm text-text placeholder:text-text-dim focus:border-accent focus:outline-none"
            required
          />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="What did you observe? Be specific — sample size, time window, market category."
            rows={3}
            className="w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-sm text-text placeholder:text-text-dim focus:border-accent focus:outline-none"
            required
          />
          <input
            type="text"
            value={recommendation}
            onChange={(e) => setRecommendation(e.target.value)}
            placeholder="Recommendation (optional) — what should the strategy do differently?"
            maxLength={500}
            className="w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-sm text-text placeholder:text-text-dim focus:border-accent focus:outline-none"
          />
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={reset}
              className="rounded-md px-3 py-1.5 text-xs text-text-dim hover:bg-surface-2 hover:text-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={create.isPending || !title.trim() || !body.trim()}
              className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-text disabled:cursor-not-allowed disabled:opacity-50"
            >
              {create.isPending ? "Saving…" : "Save finding"}
            </button>
          </div>
          {create.isError && (
            <p className="text-xs text-loss">
              Couldn't save — try again.
            </p>
          )}
        </form>
      )}

      <FindingList findings={findings ?? []} loading={isLoading} />
    </Card>
  );
}

function FindingList({
  findings,
  loading,
}: {
  findings: Insight[];
  loading: boolean;
}) {
  if (loading) return <p className="text-sm text-text-dim">Loading…</p>;
  if (findings.length === 0)
    return (
      <p className="text-sm text-text-dim">
        No findings yet. Add the first one above — even a half-formed hunch is
        worth capturing.
      </p>
    );
  return (
    <ul className="space-y-3">
      {findings.map((f) => (
        <li
          key={f.id}
          className="rounded-md border border-border/60 bg-surface-2/40 px-3 py-3"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text">{f.title}</span>
                {f.type === "manual_finding" ? (
                  <Badge className="bg-surface-3 text-text-dim">note</Badge>
                ) : (
                  <Badge className="bg-accent/15 text-accent-light">
                    {f.type.replace(/_/g, " ")}
                  </Badge>
                )}
              </div>
              <p className="mt-1 whitespace-pre-line text-xs text-text-dim">
                {f.body}
              </p>
              {f.recommendation && (
                <p className="mt-2 text-xs text-text">
                  <span className="text-text-dim">Recommendation: </span>
                  {f.recommendation}
                </p>
              )}
            </div>
            <span className="shrink-0 text-xs text-text-dim">
              {formatRelative(f.created_at)}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function TradeList({ trades }: { trades: Trade[] }) {
  if (trades.length === 0)
    return <p className="text-sm text-text-dim">No open positions.</p>;
  return (
    <ul className="space-y-2">
      {trades.map((t) => (
        <li
          key={t.id}
          className="flex items-center justify-between gap-3 rounded-md border border-border/60 bg-surface-2/40 px-3 py-2"
        >
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm text-text">
              {t.matchup ?? `Trade #${t.id}`}
            </div>
            <div className="mt-0.5 text-xs text-text-dim">
              {t.market_category} · {t.side} @ {t.entry_price}¢
            </div>
          </div>
          <Link
            to={`/trades`}
            className="shrink-0 text-xs text-accent-light hover:underline"
          >
            details →
          </Link>
        </li>
      ))}
    </ul>
  );
}

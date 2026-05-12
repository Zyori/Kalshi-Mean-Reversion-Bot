import { Link } from "react-router";
import { useMemo } from "react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useSports } from "../hooks/useSports";
import { useGames, useRecentEvents } from "../hooks/useMarkets";
import { useActiveTrades } from "../hooks/useTrades";
import { isFinalStatus, isLiveStatus, formatRelative } from "../lib/utils";
import {
  sportDisplayName,
  sportModeBadgeClass,
  sportModeLabel,
} from "../lib/sports";
import type { Game, SportEntry } from "../lib/api";

/**
 * Multi-sport overview. The top-level home view: one card per sport-by-mode,
 * each showing live/upcoming counts and a hook into the sport's own page.
 * Active sports surface first; passive next; off-mode sports hidden.
 */
export function OverviewPage() {
  const { data: sports } = useSports();
  const { data: games } = useGames({ days_ahead: 7, days_back: 1, limit: 500 });
  const { data: events } = useRecentEvents({ limit: 25 });
  const { data: activeTrades } = useActiveTrades();

  const visibleSports = useMemo(
    () =>
      (sports ?? [])
        .filter((s) => s.mode !== "off")
        .sort((a, b) => modeRank(a.mode) - modeRank(b.mode)),
    [sports],
  );

  const gamesBySport = useMemo(() => groupBySport(games ?? []), [games]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            All sports
          </h2>
          <p className="mt-1 text-sm text-text-dim">
            Bot engagement at a glance. Active sports run the full pipeline;
            passive sports collect schedules and opening lines only.
          </p>
        </div>
        <div className="text-xs text-text-dim">
          {games?.length ?? 0} games · {events?.length ?? 0} recent events ·{" "}
          {activeTrades?.length ?? 0} open trades
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {visibleSports.map((entry) => (
          <SportCard
            key={entry.sport}
            entry={entry}
            games={gamesBySport[entry.sport] ?? []}
          />
        ))}
        {visibleSports.length === 0 && (
          <Card className="md:col-span-2 lg:col-span-3 text-sm text-text-dim">
            No sports are currently active or passive. Update{" "}
            <span className="font-mono">sport_configs</span> to engage one.
          </Card>
        )}
      </section>
    </div>
  );
}

function modeRank(mode: SportEntry["mode"]): number {
  if (mode === "active") return 0;
  if (mode === "passive") return 1;
  return 2;
}

function groupBySport(games: Game[]): Record<string, Game[]> {
  const out: Record<string, Game[]> = {};
  for (const g of games) {
    (out[g.sport] ??= []).push(g);
  }
  return out;
}

function SportCard({ entry, games }: { entry: SportEntry; games: Game[] }) {
  const counts = useMemo(() => {
    let live = 0;
    let upcoming = 0;
    let nextStart: string | null = null;
    for (const g of games) {
      if (isLiveStatus(g.status)) live++;
      else if (!isFinalStatus(g.status)) {
        upcoming++;
        if (!nextStart || g.start_time < nextStart) nextStart = g.start_time;
      }
    }
    return { live, upcoming, nextStart };
  }, [games]);

  return (
    <Link
      to={`/sports/${entry.sport}`}
      className="group block rounded-lg border border-border bg-surface-1 p-5 transition-colors hover:border-accent/40 hover:bg-surface-2"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold text-text">
          {sportDisplayName(entry.sport)}
        </h3>
        <Badge className={sportModeBadgeClass(entry.mode)}>
          {sportModeLabel(entry.mode)}
        </Badge>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <Metric label="Live" value={counts.live} accent={counts.live > 0} />
        <Metric label="Upcoming" value={counts.upcoming} />
      </div>

      <div className="mt-4 text-xs text-text-dim">
        {counts.live > 0
          ? "Bot is watching live games"
          : counts.nextStart
            ? `Next ${formatRelative(counts.nextStart)}`
            : "No games scheduled in window"}
      </div>
    </Link>
  );
}

function Metric({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div className="rounded-md border border-border/60 bg-surface-2/40 px-3 py-2">
      <div className="text-xs text-text-dim">{label}</div>
      <div
        className={`mt-0.5 font-mono text-lg ${accent ? "text-profit" : "text-text"}`}
      >
        {value}
      </div>
    </div>
  );
}

import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import { StatCard } from "../components/ui/StatCard";
import { useStrategyCatalog } from "../hooks/useStrategy";
import { formatCents } from "../lib/utils";

const MARKET_LABELS: Record<string, string> = {
  moneyline: "Moneyline",
  spread: "Spread",
  total: "Total",
  team_total: "Team Total",
};

const MARKET_STATUS_STYLES: Record<string, string> = {
  live: "bg-profit/20 text-profit",
  conditional: "bg-amber-500/15 text-amber-300",
  planned: "bg-surface-3 text-text-dim",
};

function formatSeconds(value: number): string {
  if (value >= 3600) return `${(value / 3600).toFixed(value % 3600 === 0 ? 0 : 1)}h`;
  if (value >= 60) return `${(value / 60).toFixed(value % 60 === 0 ? 0 : 1)}m`;
  return `${value.toFixed(0)}s`;
}

function formatThreshold(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatParamName(key: string): string {
  return key.replaceAll("_", " ");
}

export function StrategyPage() {
  const { data, isLoading } = useStrategyCatalog();

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="grid gap-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  const tradePolicyByCategory = Object.fromEntries(
    data.trade_policy.markets.map((market) => [market.market_category, market]),
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Strategy</h2>
          <p className="text-sm text-text-dim">
            Live strategy catalog pulled from backend rules. This page updates
            automatically when thresholds or classifier defaults change.
          </p>
        </div>
        <Badge className="bg-accent/15 text-accent-light">
          Platform TZ {data.platform_timezone}
        </Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <StatCard
          label="Mock Bank"
          value={formatCents(data.trade_policy.paper_bankroll_start_cents)}
          subtext="Sticky paper bankroll base"
        />
        <StatCard
          label="Schedule Sync"
          value={formatSeconds(data.collection.schedule_poll_interval_s)}
          subtext="Opening lines and schedule refresh"
        />
        <StatCard
          label="Live Scoreboard"
          value={formatSeconds(data.collection.live_scoreboard_poll_interval_s)}
          subtext="Active game status polling"
        />
        <StatCard
          label="Open Limit"
          value={String(data.trade_policy.max_open_per_market)}
          subtext={`${data.trade_policy.reentry_min_price_move_cents}c minimum re-entry move`}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-text-dim">Trade Rails</h3>
            <span className="text-xs text-text-dim">
              Confidence and deviation gates
            </span>
          </div>
          <div className="space-y-3">
            {data.trade_policy.markets.map((market) => (
              <div
                key={market.market_category}
                className="rounded-lg border border-border bg-surface-2 p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-accent/15 text-accent-light">
                      {MARKET_LABELS[market.market_category] ?? market.market_category}
                    </Badge>
                    <Badge
                      className={
                        MARKET_STATUS_STYLES[market.status] ??
                        MARKET_STATUS_STYLES.planned
                      }
                    >
                      {market.status === "conditional" ? "Conditional" : "Live"}
                    </Badge>
                    <span className="text-xs text-text-dim">{market.source}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-text-dim">
                    <span>Confidence {formatThreshold(market.confidence_threshold)}</span>
                    <span>Deviation {formatThreshold(market.deviation_threshold)}</span>
                  </div>
                </div>
                <p className="mt-2 text-sm text-text-dim">{market.summary}</p>
                <p className="mt-2 text-xs text-text-dim">{market.status_note}</p>
              </div>
            ))}
          </div>
          <div className="rounded-lg border border-border bg-surface-2 p-4">
            <h4 className="text-xs font-medium uppercase tracking-wide text-text-dim">
              Policy Notes
            </h4>
            <div className="mt-3 space-y-2 text-sm text-text-dim">
              {data.trade_policy.notes.map((note) => (
                <p key={note}>{note}</p>
              ))}
            </div>
          </div>
        </Card>

        <div className="space-y-4">
          <Card className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-text-dim">Collection Cadence</h3>
              <span className="text-xs text-text-dim">Adaptive polling</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg bg-surface-2 p-3">
                <p className="text-xs uppercase tracking-wide text-text-dim">Pregame</p>
                <p className="mt-1 font-mono text-lg">
                  {formatSeconds(data.collection.pregame_poll_interval_s)}
                </p>
              </div>
              <div className="rounded-lg bg-surface-2 p-3">
                <p className="text-xs uppercase tracking-wide text-text-dim">Live Events</p>
                <p className="mt-1 font-mono text-lg">
                  {formatSeconds(data.collection.live_events_poll_interval_s)}
                </p>
              </div>
            </div>
            <p className="text-sm text-text-dim">{data.collection.note}</p>
          </Card>

          <Card className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-text-dim">Event Filters</h3>
              <span className="text-xs text-text-dim">Shared trigger vocabulary</span>
            </div>
            <div className="space-y-3">
              {[
                { label: "Scoring", tokens: data.event_filters.scoring_tokens },
                {
                  label: "High Leverage",
                  tokens: data.event_filters.high_leverage_tokens,
                },
                {
                  label: "Structural Shift",
                  tokens: data.event_filters.structural_shift_tokens,
                },
              ].map((group) => (
                <div key={group.label} className="rounded-lg bg-surface-2 p-3">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-dim">
                    {group.label}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {group.tokens.map((token) => (
                      <Badge
                        key={token}
                        className="bg-surface-3 text-text-dim normal-case"
                      >
                        {token}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-text-dim">Sport Playbooks</h3>
            <p className="text-xs text-text-dim">
              Moneyline defaults plus rail-specific candidate bands by sport
            </p>
          </div>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          {data.sports.map((sport) => (
            <Card key={sport.sport} className="space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-base font-semibold">{sport.display_name}</h4>
                    <Badge className="bg-surface-3 text-text-dim">
                      {sport.segments} segments
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm text-text-dim">{sport.summary}</p>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-surface-2 p-4">
                <div className="flex items-center justify-between gap-3">
                  <h5 className="text-sm font-medium">Moneyline</h5>
                  <Badge
                    className={
                      MARKET_STATUS_STYLES[
                        tradePolicyByCategory.moneyline?.status ?? "planned"
                      ] ?? MARKET_STATUS_STYLES.planned
                    }
                  >
                    {tradePolicyByCategory.moneyline?.status === "conditional"
                      ? "Conditional"
                      : "Live"}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-text-dim">{sport.moneyline.summary}</p>
                <p className="mt-2 text-xs text-text-dim">
                  {tradePolicyByCategory.moneyline?.status_note}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {Object.entries(sport.moneyline.params).map(([key, value]) => (
                    <Badge
                      key={key}
                      className="bg-surface-3 text-text-dim normal-case"
                    >
                      {formatParamName(key)} {value}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                {sport.markets.map((market) => {
                  const marketPolicy = tradePolicyByCategory[market.market_category];
                  return (
                  <div
                    key={market.market_category}
                    className="rounded-lg border border-border bg-surface-2 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <h5 className="text-sm font-medium">
                          {MARKET_LABELS[market.market_category] ?? market.market_category}
                        </h5>
                        {marketPolicy ? (
                          <Badge
                            className={
                              MARKET_STATUS_STYLES[marketPolicy.status] ??
                              MARKET_STATUS_STYLES.planned
                            }
                          >
                            {marketPolicy.status === "conditional"
                              ? "Conditional"
                              : "Live"}
                          </Badge>
                        ) : null}
                      </div>
                      {market.candidate_edge_min != null &&
                      market.candidate_edge_max != null ? (
                        <span className="text-xs text-text-dim">
                          Candidate band {market.candidate_edge_min.toFixed(1)}-
                          {market.candidate_edge_max.toFixed(1)}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm text-text-dim">{market.summary}</p>
                    {marketPolicy?.status_note ? (
                      <p className="mt-2 text-xs text-text-dim">
                        {marketPolicy.status_note}
                      </p>
                    ) : null}
                    {market.structural_edge != null && (
                      <div className="mt-3 flex items-center gap-4 text-xs text-text-dim">
                        <span>
                          Structural shift at {market.structural_edge.toFixed(1)}
                        </span>
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

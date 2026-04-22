import {
  useAnalysisSummary,
  useAnalysisBySport,
  useAnalysisByEventType,
  useAnalysisByMarketCategory,
  useRecentEventAudit,
  useSkipReasons,
  useDecisionSummary,
  useEquityCurve,
  useKellyComparison,
  useInsights,
} from "../hooks/useAnalytics";
import { Card } from "../components/ui/Card";
import { StatCard } from "../components/ui/StatCard";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { EquityCurve } from "../components/charts/EquityCurve";
import { KellyComparison } from "../components/charts/KellyComparison";
import { SportBreakdownChart } from "../components/charts/SportBreakdownChart";
import { formatCents, formatPnl, formatPercent, formatDate, pnlColor } from "../lib/utils";

function InsightTypeBadge({ type }: { type: string }) {
  const styles: Record<string, string> = {
    edge_validated: "bg-profit/20 text-profit",
    edge_degraded: "bg-loss/20 text-loss",
    parameter_recommendation: "bg-accent/20 text-accent-light",
    anomaly_detected: "bg-yellow-500/20 text-yellow-400",
  };
  return (
    <Badge className={styles[type] ?? "bg-surface-2 text-text-dim"}>
      {type.replace(/_/g, " ")}
    </Badge>
  );
}

export function AnalyticsPage() {
  const { data: summary, isLoading: loadingSummary } = useAnalysisSummary();
  const { data: bySport } = useAnalysisBySport();
  const { data: byEventType } = useAnalysisByEventType();
  const { data: byMarketCategory } = useAnalysisByMarketCategory();
  const { data: eventAudit } = useRecentEventAudit();
  const { data: skipReasons } = useSkipReasons();
  const { data: decisionSummary } = useDecisionSummary();
  const { data: equity } = useEquityCurve();
  const { data: kelly } = useKellyComparison();
  const { data: insights } = useInsights();

  if (loadingSummary) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Analytics</h2>

      {summary && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Total Trades"
            value={String(summary.total_trades)}
            subtext={`${summary.open} open`}
          />
          <StatCard
            label="Win Rate"
            value={formatPercent(summary.win_rate)}
            subtext={`${summary.wins}W / ${summary.losses}L / ${summary.pushes}P`}
            className={
              summary.win_rate > 0.5
                ? "text-profit"
                : summary.win_rate < 0.5
                  ? "text-loss"
                  : ""
            }
          />
          <StatCard
            label="Total PnL"
            value={formatPnl(summary.total_pnl_cents)}
            className={pnlColor(summary.total_pnl_cents)}
            subtext={`Bank ${formatPnl(summary.current_bankroll_cents - summary.starting_bankroll_cents)} vs start`}
          />
          <StatCard
            label="Resolved"
            value={String(summary.resolved)}
            subtext={`${summary.open} pending`}
          />
          <StatCard
            label="Mock Bank"
            value={formatCents(summary.current_bankroll_cents)}
            subtext={`Avail ${formatCents(summary.available_bankroll_cents)} / Held ${formatCents(summary.pending_wagers_cents)}`}
          />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-sm font-medium text-text-dim">
            Equity Curve
          </h3>
          <EquityCurve data={equity ?? []} />
        </Card>
        <Card>
          <h3 className="mb-3 text-sm font-medium text-text-dim">
            Kelly vs Flat Sizing
          </h3>
          <KellyComparison data={kelly ?? []} />
        </Card>
      </div>

      <Card>
        <h3 className="mb-3 text-sm font-medium text-text-dim">
          PnL by Sport
        </h3>
        <SportBreakdownChart data={bySport ?? []} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-sm font-medium text-text-dim">
            Trigger Events
          </h3>
          {!byEventType || byEventType.length === 0 ? (
            <p className="text-sm text-text-dim">No resolved trigger data yet</p>
          ) : (
            <div className="space-y-2">
              {byEventType.slice(0, 8).map((row) => (
                <div
                  key={row.event_type}
                  className="flex items-center justify-between rounded-md bg-surface-2 px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium">{row.event_type}</p>
                    <p className="text-xs text-text-dim">{row.count} resolved trades</p>
                  </div>
                  <span className={`font-mono text-sm ${pnlColor(row.total_pnl_cents)}`}>
                    {formatPnl(row.total_pnl_cents)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-medium text-text-dim">
            Market Rails
          </h3>
          {!byMarketCategory || byMarketCategory.length === 0 ? (
            <p className="text-sm text-text-dim">No resolved rail data yet</p>
          ) : (
            <div className="space-y-2">
              {byMarketCategory.map((row) => (
                <div
                  key={row.market_category}
                  className="flex items-center justify-between rounded-md bg-surface-2 px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium uppercase">{row.market_category}</p>
                    <p className="text-xs text-text-dim">{row.count} resolved trades</p>
                  </div>
                  <span className={`font-mono text-sm ${pnlColor(row.total_pnl_cents)}`}>
                    {formatPnl(row.total_pnl_cents)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <h3 className="mb-3 text-sm font-medium text-text-dim">
          Recent Classification Audit
        </h3>
        {!eventAudit || eventAudit.length === 0 ? (
          <p className="text-sm text-text-dim">No recent event audit data yet</p>
        ) : (
          <div className="grid gap-2 md:grid-cols-3">
            {eventAudit.map((row) => (
              <div
                key={`${row.market_category}-${row.classification}`}
                className="rounded-md bg-surface-2 px-3 py-2"
              >
                <p className="text-xs uppercase text-text-dim">{row.market_category}</p>
                <p className="text-sm font-medium">{row.classification}</p>
                <p className="text-xs text-text-dim">{row.count} recent events</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-sm font-medium text-text-dim">
            Trade Decisions
          </h3>
          {!decisionSummary || decisionSummary.length === 0 ? (
            <p className="text-sm text-text-dim">No trade decision data yet</p>
          ) : (
            <div className="space-y-2">
              {decisionSummary.map((row) => (
                <div
                  key={`${row.market_category}-${row.action}`}
                  className="flex items-center justify-between rounded-md bg-surface-2 px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium uppercase">{row.market_category}</p>
                    <p className="text-xs text-text-dim">{row.action}</p>
                  </div>
                  <span className="font-mono text-sm">{row.count}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-medium text-text-dim">
            Skip Reasons
          </h3>
          {!skipReasons || skipReasons.length === 0 ? (
            <p className="text-sm text-text-dim">No skipped trade data yet</p>
          ) : (
            <div className="space-y-2">
              {skipReasons.slice(0, 10).map((row) => (
                <div
                  key={`${row.market_category}-${row.skip_reason}`}
                  className="flex items-center justify-between rounded-md bg-surface-2 px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium">{row.skip_reason}</p>
                    <p className="text-xs uppercase text-text-dim">{row.market_category}</p>
                  </div>
                  <span className="font-mono text-sm">{row.count}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {insights && insights.length > 0 && (
        <Card>
          <h3 className="mb-3 text-sm font-medium text-text-dim">
            Insights
          </h3>
          <div className="space-y-3">
            {insights.map((ins) => (
              <div
                key={ins.id}
                className="rounded-md border border-border/50 bg-surface-2/50 p-3"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <InsightTypeBadge type={ins.type} />
                    <span className="text-sm font-medium">{ins.title}</span>
                  </div>
                  <span className="text-xs text-text-dim">
                    {formatDate(ins.created_at)}
                  </span>
                </div>
                <p className="text-xs text-text-dim">{ins.body}</p>
                {ins.recommendation && (
                  <p className="mt-1 text-xs text-accent-light">
                    {ins.recommendation}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

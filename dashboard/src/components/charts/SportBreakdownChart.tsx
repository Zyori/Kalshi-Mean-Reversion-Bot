import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import type { SportBreakdown } from "../../lib/api";

export function SportBreakdownChart({ data }: { data: SportBreakdown[] }) {
  if (data.length === 0) {
    return (
      <div className="flex h-[250px] items-center justify-center text-text-dim text-sm">
        No data yet
      </div>
    );
  }

  const mapped = data.map((d) => ({
    sport: d.sport,
    pnl: d.total_pnl_cents / 100,
    count: d.count,
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={mapped}>
        <XAxis
          dataKey="sport"
          stroke="#71717a"
          fontSize={11}
          tickLine={false}
        />
        <YAxis
          stroke="#71717a"
          fontSize={11}
          tickLine={false}
          tickFormatter={(v: number) => `$${v.toFixed(0)}`}
        />
        <Tooltip
          contentStyle={{
            background: "#12131a",
            border: "1px solid #2a2b36",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(v) => [`$${Number(v).toFixed(2)}`, "PnL"]}
        />
        <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
          {mapped.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.pnl >= 0 ? "#22c55e" : "#ef4444"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

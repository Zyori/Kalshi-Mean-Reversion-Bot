import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";
import type { KellyPoint } from "../../lib/api";

export function KellyComparison({ data }: { data: KellyPoint[] }) {
  if (data.length === 0) {
    return (
      <div className="flex h-[250px] items-center justify-center text-text-dim text-sm">
        No data yet
      </div>
    );
  }

  const mapped = data.map((p, i) => ({
    idx: i + 1,
    kelly: p.kelly / 100,
    flat: p.flat / 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={mapped}>
        <XAxis
          dataKey="idx"
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
          formatter={(v) => [`$${Number(v).toFixed(2)}`, undefined]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="kelly"
          stroke="#6366f1"
          strokeWidth={2}
          dot={false}
          name="Kelly"
        />
        <Line
          type="monotone"
          dataKey="flat"
          stroke="#22c55e"
          strokeWidth={2}
          dot={false}
          name="Flat $5"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

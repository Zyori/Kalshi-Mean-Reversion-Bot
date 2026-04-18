import { useEffect, useRef } from "react";
import { createChart, type IChartApi, ColorType, AreaSeries } from "lightweight-charts";
import type { EquityPoint } from "../../lib/api";

export function EquityCurve({ data }: { data: EquityPoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#71717a",
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: "#1a1b24" },
        horzLines: { color: "#1a1b24" },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
      },
      crosshair: {
        horzLine: { color: "#6366f1", width: 1, style: 2 },
        vertLine: { color: "#6366f1", width: 1, style: 2 },
      },
    });
    chartRef.current = chart;

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#6366f1",
      topColor: "rgba(99, 102, 241, 0.3)",
      bottomColor: "rgba(99, 102, 241, 0.02)",
      lineWidth: 2,
    });

    const mapped = data
      .filter((p) => p.time)
      .map((p) => ({
        time: p.time!.slice(0, 10) as string,
        value: p.pnl / 100,
      }));

    if (mapped.length > 0) {
      series.setData(mapped as Parameters<typeof series.setData>[0]);
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center text-text-dim text-sm">
        No resolved trades yet
      </div>
    );
  }

  return <div ref={containerRef} />;
}

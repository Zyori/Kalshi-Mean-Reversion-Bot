import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  createColumnHelper,
  flexRender,
  type SortingState,
} from "@tanstack/react-table";
import { useTrades } from "../hooks/useTrades";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import {
  formatCents,
  formatPnl,
  formatDate,
  formatPercent,
  pnlColor,
  statusBadgeClass,
} from "../lib/utils";
import type { Trade } from "../lib/api";

const col = createColumnHelper<Trade>();

const columns = [
  col.accessor("entered_at", {
    header: "Time",
    cell: (info) => (
      <span className="text-xs text-text-dim whitespace-nowrap">
        {formatDate(info.getValue())}
      </span>
    ),
  }),
  col.accessor("sport", {
    header: "Sport",
    cell: (info) => (
      <Badge className="bg-surface-2 text-text-dim uppercase text-[10px]">
        {info.getValue()}
      </Badge>
    ),
  }),
  col.accessor("side", {
    header: "Side",
    cell: (info) => <span className="uppercase text-xs">{info.getValue()}</span>,
  }),
  col.accessor("entry_price", {
    header: () => <span className="text-right w-full block">Entry</span>,
    cell: (info) => (
      <span className="font-mono tabular-nums text-right block">
        {formatCents(info.getValue())}
      </span>
    ),
  }),
  col.accessor("entry_price_adj", {
    header: () => <span className="text-right w-full block">Adj</span>,
    cell: (info) => (
      <span className="font-mono tabular-nums text-right block text-text-dim">
        {formatCents(info.getValue())}
      </span>
    ),
  }),
  col.accessor("confidence_score", {
    header: () => <span className="text-right w-full block">Conf</span>,
    cell: (info) => (
      <span className="font-mono tabular-nums text-right block">
        {formatPercent(info.getValue())}
      </span>
    ),
  }),
  col.accessor("kelly_fraction", {
    header: () => <span className="text-right w-full block">Kelly f</span>,
    cell: (info) => (
      <span className="font-mono tabular-nums text-right block text-text-dim">
        {formatPercent(info.getValue())}
      </span>
    ),
  }),
  col.accessor("pnl_cents", {
    header: () => <span className="text-right w-full block">PnL</span>,
    cell: (info) => (
      <span
        className={`font-mono tabular-nums text-right block font-medium ${pnlColor(info.getValue())}`}
      >
        {formatPnl(info.getValue())}
      </span>
    ),
  }),
  col.accessor("status", {
    header: "Status",
    cell: (info) => (
      <Badge className={statusBadgeClass(info.getValue())}>
        {info.getValue().replace("resolved_", "")}
      </Badge>
    ),
  }),
];

export function TradesPage() {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "entered_at", desc: true },
  ]);
  const { data: trades, isLoading, dataUpdatedAt } = useTrades({ limit: 100 });

  const table = useReactTable({
    data: useMemo(() => trades ?? [], [trades]),
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Paper Trades</h2>
        {dataUpdatedAt > 0 && (
          <span className="text-xs text-text-dim">
            Updated {new Date(dataUpdatedAt).toLocaleTimeString()}
          </span>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-border bg-surface-1">
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className="cursor-pointer select-none px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-dim hover:text-text"
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      {{
                        asc: " \u2191",
                        desc: " \u2193",
                      }[header.column.getIsSorted() as string] ?? ""}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-3 py-12 text-center text-text-dim"
                >
                  No trades yet
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-border/50 hover:bg-surface-2/50 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { Card } from "./Card";

export function StatCard({
  label,
  value,
  subtext,
  className = "",
}: {
  label: string;
  value: string;
  subtext?: string;
  className?: string;
}) {
  return (
    <Card>
      <p className="text-xs font-medium text-text-dim uppercase tracking-wider">
        {label}
      </p>
      <p className={`mt-1 text-2xl font-semibold font-mono tabular-nums ${className}`}>
        {value}
      </p>
      {subtext && (
        <p className="mt-0.5 text-xs text-text-dim">{subtext}</p>
      )}
    </Card>
  );
}

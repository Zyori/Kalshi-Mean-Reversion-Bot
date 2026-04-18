export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-surface-2 ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}

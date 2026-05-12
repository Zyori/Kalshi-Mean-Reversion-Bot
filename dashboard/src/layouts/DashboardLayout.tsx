import { NavLink, Outlet } from "react-router";
import { useHealth } from "../hooks/useHealth";
import { useSports } from "../hooks/useSports";
import { useAuth } from "../hooks/useAuth";
import {
  sportDisplayName,
  sportModeBadgeClass,
  sportModeLabel,
} from "../lib/sports";

const SECONDARY_NAV = [
  { to: "/markets", label: "Markets" },
  { to: "/data", label: "Data" },
  { to: "/trades", label: "Trades" },
  { to: "/strategy", label: "Strategy" },
  { to: "/analytics", label: "Analytics" },
] as const;

export function DashboardLayout() {
  const { data: health } = useHealth();
  const { data: sports } = useSports();
  const { logout } = useAuth();

  const visibleSports = (sports ?? []).filter((s) => s.mode !== "off");
  const staleLoops = health?.loops?.filter((l) => l.stale) ?? [];
  const overallStatus =
    health?.status === "ok"
      ? "Connected"
      : health?.status === "degraded"
        ? "Degraded"
        : "Disconnected";
  const overallDotClass =
    health?.status === "ok"
      ? "bg-profit"
      : health?.status === "degraded"
        ? "bg-amber-400"
        : "bg-loss";

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 border-b border-border bg-surface-0/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex flex-wrap items-center gap-4">
            <NavLink to="/" className="flex items-center gap-2">
              <h1 className="text-base font-semibold tracking-tight text-text">
                Lutz Bot
              </h1>
            </NavLink>
            <nav className="flex flex-wrap gap-1">
              <NavLink to="/" end className={navLinkClass}>
                Overview
              </NavLink>
              {visibleSports.map((s) => (
                <NavLink
                  key={s.sport}
                  to={`/sports/${s.sport}`}
                  className={navLinkClass}
                  title={sportModeLabel(s.mode)}
                >
                  <span className="inline-flex items-center gap-1.5">
                    {sportDisplayName(s.sport)}
                    <span
                      className={`inline-block h-1.5 w-1.5 rounded-full ${
                        s.mode === "active"
                          ? "bg-profit"
                          : s.mode === "passive"
                            ? "bg-accent"
                            : "bg-zinc-500"
                      }`}
                    />
                  </span>
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4 text-xs text-text-dim">
            <div
              className="flex items-center gap-2"
              title={
                staleLoops.length
                  ? `Stale: ${staleLoops.map((l) => l.name).join(", ")}`
                  : `${health?.loops?.length ?? 0} loops running`
              }
            >
              <span
                className={`inline-block h-2 w-2 rounded-full ${overallDotClass}`}
              />
              {overallStatus}
              {staleLoops.length > 0 && (
                <span className="text-amber-400">
                  · {staleLoops.length} stale
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => logout.mutate()}
              className="rounded-md px-2 py-1 hover:bg-surface-2 hover:text-text"
            >
              Sign out
            </button>
          </div>
        </div>
        <div className="border-t border-border/60 bg-surface-0/60">
          <div className="mx-auto flex max-w-7xl gap-1 px-4 py-2 text-xs">
            {SECONDARY_NAV.map((item) => (
              <NavLink key={item.to} to={item.to} className={subNavLinkClass}>
                {item.label}
              </NavLink>
            ))}
            {sports && (
              <span className="ml-auto self-center text-text-dim">
                {visibleSports.length} sports tracked
              </span>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive
      ? "bg-accent/15 text-accent-light"
      : "text-text-dim hover:text-text hover:bg-surface-2"
  }`;
}

function subNavLinkClass({ isActive }: { isActive: boolean }): string {
  return `rounded px-2 py-1 transition-colors ${
    isActive
      ? "bg-surface-2 text-text"
      : "text-text-dim hover:text-text hover:bg-surface-2/60"
  }`;
}

// Re-export for any callers that previously imported via DashboardLayout.
export { sportModeBadgeClass };

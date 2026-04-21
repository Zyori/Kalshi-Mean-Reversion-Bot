import { NavLink, Outlet } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuth } from "../hooks/useAuth";

const NAV_ITEMS = [
  { to: "/", label: "Markets" },
  { to: "/trades", label: "Trades" },
  { to: "/analytics", label: "Analytics" },
] as const;

export function DashboardLayout() {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 10_000,
  });
  const { logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 border-b border-border bg-surface-0/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <h1 className="text-base font-semibold tracking-tight text-text">
              Kalshi MRB
            </h1>
            <nav className="flex gap-1">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-accent/15 text-accent-light"
                        : "text-text-dim hover:text-text hover:bg-surface-2"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4 text-xs text-text-dim">
            <div className="flex items-center gap-2">
              <span
                className={`inline-block h-2 w-2 rounded-full ${
                  health?.status === "ok" ? "bg-profit" : "bg-loss"
                }`}
              />
              {health?.status === "ok" ? "Connected" : "Disconnected"}
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
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

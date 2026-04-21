import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { authed, login } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (authed === true) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login.mutateAsync(password);
      navigate("/", { replace: true });
    } catch {
      setError("Invalid password.");
      setPassword("");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-lg border border-border bg-surface-1 p-6 shadow-lg"
      >
        <h1 className="mb-1 text-lg font-semibold tracking-tight">Lutz MRB</h1>
        <p className="mb-6 text-sm text-text-dim">Sign in to continue.</p>
        <label className="block text-xs font-medium text-text-dim mb-1" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoFocus
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-sm outline-none focus:border-accent"
        />
        {error && <p className="mt-2 text-xs text-loss">{error}</p>}
        <button
          type="submit"
          disabled={login.isPending || !password}
          className="mt-4 w-full rounded-md bg-accent px-3 py-2 text-sm font-medium text-black transition-opacity disabled:opacity-50"
        >
          {login.isPending ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

# Dashboard

The operator and public build-log frontend for the Kalshi sports trading
research bot. See the [project README](../README.md) for the full system
overview.

## Stack

React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query + Table,
Lightweight Charts, and Recharts.

## Develop

```bash
nvm use            # Node 22 via .nvmrc
npm install
npm run dev        # http://localhost:5173
```

The dev server proxies `/api` to the backend at `localhost:8000`, so run the
backend (see the project README) alongside it.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start the Vite dev server with HMR |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Run ESLint |

## Layout

```
src/
  pages/        # Overview, per-Sport, Strategy, Analytics, Trades, Markets, Data, public status, login
  components/   # Charts (equity curve, sizing comparison, sport breakdown) and UI primitives
  hooks/        # TanStack Query hooks with polling
  layouts/      # Shared dashboard shell
  lib/          # Typed API client, sport metadata, formatters
```

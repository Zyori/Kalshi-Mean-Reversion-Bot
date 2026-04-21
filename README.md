# Kalshi Mean Reversion Bot

A sports market research bot for collecting sportsbook baselines, live game events, and paper-trading signals for future mean-reversion work on [Kalshi](https://kalshi.com).

**Phase 1** is focused on durable data collection and paper-trade scaffolding. The backend now persists schedules, opening lines, and detected ESPN events so the project can run continuously and build a dataset before real-money trading is considered.

## How It Works

```
ESPN Scoreboard → keeps schedules and live game states in sync
ESPN Events     → detects significant live game events
The Odds API    → captures pre-game sportsbook lines as baselines
Kalshi REST/WS  → adapter layer exists, demo-first by default
                    ↓
Strategy Engine → classifies events (reversion_candidate / structural_shift / neutral)
                → scores opportunities once Kalshi price data is attached
                    ↓
Paper Trader    → quarter-Kelly sizing with Bayesian edge shrinkage
                → slippage model (0.5% + depth adjustment)
                → currently scaffolded behind the ingestion layer
                    ↓
Analysis Engine → binomial test (win rate > 50%)
                → t-test (mean PnL > $0)
                → regime change detection (last 30 vs all-time)
                → logs insights to DB when thresholds crossed
                    ↓
Dashboard       → Markets / Trades / Analytics views
                → equity curve, Kelly comparison, sport breakdown
```

## Current Phase-1 Status

- Persisted today: games, opening lines, and significant ESPN events.
- Adaptive polling: idle schedule sync backs off heavily, live games poll quickly.
- Auth: password-protected admin backend with separate public status endpoints.
- Kalshi mode: configured for `demo` by default, but live market snapshot capture is still an integration step rather than a finished data path.

This means the project is ready to start building a historical dataset, but not yet ready to claim end-to-end market replay or meaningful paper-trade analytics from Kalshi prices.

## Sports Covered

NHL, NBA, MLB, NFL, Soccer (EPL), UFC are recognized by the collectors and classifiers. NHL is still the best first target because the event data is richer and cleaner.

## Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy (async), aiosqlite, Alembic, structlog, scipy, pandas

**Dashboard:** React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query + Table, Lightweight Charts, Recharts

## Setup

### Backend

```bash
cd backend
cp .env.example .env        # fill in API keys
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

### Dashboard

```bash
cd dashboard
nvm use                      # Node 22 via .nvmrc
npm install
npm run dev                  # http://localhost:5173
```

The dashboard proxies `/api` requests to the backend at `localhost:8000`.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `KALSHI_KEY_ID` | Yes | Kalshi API key ID |
| `KALSHI_PRIVATE_KEY_PATH` | Yes | Path to RSA private key PEM file |
| `KALSHI_ENVIRONMENT` | No | `demo` (default) or `prod` |
| `ODDS_API_KEY` | Yes | The Odds API key (free tier: 500 req/month) |
| `DATABASE_URL` | No | Defaults to `sqlite+aiosqlite:///./data/bot.db` |
| `SCOREBOARD_LIVE_POLL_INTERVAL_S` | No | Live-game scoreboard cadence, default `10` |
| `SCOREBOARD_PREGAME_POLL_INTERVAL_S` | No | Pregame cadence, default `300` |
| `SCOREBOARD_IDLE_POLL_INTERVAL_S` | No | Idle schedule-sync cadence, default `43200` |
| `ODDS_POLL_INTERVAL_S` | No | Opening-line sync cadence, default `43200` |
| `EVENTS_POLL_INTERVAL_S` | No | Live event cadence for watched games, default `15` |

## Testing

```bash
cd backend
uv run pytest tests/ -v      # 99 tests
uv run ruff check .          # linting
uv run ruff format --check . # formatting
```

## Project Structure

```
backend/
  src/
    ingestion/     # Kalshi REST/WS, ESPN scoreboard/events, Odds API
    strategy/      # Event detector, classifier, scorer, 6 sport classifiers
    paper_trader/  # Kelly sizing, portfolio tracking, trade simulator
    analysis/      # Accumulators, significance tests, insight generation
    api/routes/    # REST endpoints (games, trades, analysis, config)
    services/      # Trade and config query services
    models/        # SQLAlchemy ORM (7 tables)
    core/          # Auth, DB, types, exceptions, logging
  tests/           # 99 tests across strategy, paper trader, analysis, API
  alembic/         # Async migrations
dashboard/
  src/
    pages/         # Markets, Trades, Analytics
    components/    # Charts (equity curve, Kelly, sport breakdown), UI primitives
    hooks/         # TanStack Query hooks with polling
    lib/           # Typed API client, formatters
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health and data source status |
| GET | `/api/games` | Active games (filterable by sport/status) |
| GET | `/api/games/{id}` | Game detail with events and opening lines |
| GET | `/api/events` | Recent events (filterable by sport/type) |
| GET | `/api/trades` | Paper trade history (sortable, filterable) |
| GET | `/api/trades/active` | Open positions |
| GET | `/api/analysis/summary` | Win rate, PnL, trade counts |
| GET | `/api/analysis/equity-curve` | Cumulative PnL time series |
| GET | `/api/analysis/kelly-comparison` | Kelly vs flat sizing comparison |
| GET | `/api/insights` | Statistical insights log |
| PATCH | `/api/config/{key}` | Update strategy parameter |

## Notes

This is a public build log as much as a trading project. Keep credentials out of the repo, keep the Kalshi key material outside the tree, and prefer small documented commits from `main`.

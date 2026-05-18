# Kalshi Sports Trading Research Bot

A sports-market research bot that collects sportsbook baselines and live game
events, then paper-trades directional signals against real
[Kalshi](https://kalshi.com) orderbook prices. The goal is a clean,
statistically honest dataset: trade live, measure every edge, and let the data
say which signals are worth real money.

The project began as a pure mean-reversion bet — fade the market's overreaction
to in-game events. That single thesis didn't hold up, so the strategy layer
evolved into a **registry of named edges** that test competing directions
(reversion *and* continuation) side by side, each tagged so its win rate and
P&L can be measured independently.

## How It Works

```
ESPN Scoreboard → keeps schedules and live game states in sync
ESPN Events     → detects significant live game events (goals, cards, etc.)
The Odds API    → captures pre-game sportsbook lines as probability baselines
Kalshi REST/WS  → real orderbook prices; demo environment by default
                    ↓
Strategy Engine → per-sport edge registry — small modules, one per hypothesis
                → each edge inspects game state + baseline and may fire a
                  directional signal tagged with its signal_kind
                    ↓
Paper Trader    → records a paper bet against the real Kalshi ask
                → flat sizing in the research phase (equal-weight trades keep
                  per-edge stats comparable); Kelly sizing available
                → slippage model on entry price
                    ↓
Analysis Engine → analyzer registry — small modules, one per question
                → per-edge health, edge decay, unprofitability, league skew
                → significance tests (binomial, t-test) gate findings
                → writes findings to the insights table for operator review
                    ↓
Dashboard       → sport-first overview, per-sport pages, strategy catalog,
                  analytics (equity curve, sizing comparison), trade history
```

## Current Status

This is a research-phase build log. It runs continuously to accumulate a
historical dataset and a Kalshi price time series before any real-money
trading is considered.

- **Persisted:** games, opening lines, ESPN game events, Kalshi orderbook
  snapshots (event-driven *and* periodic time-series), paper trades, and
  per-sport statistical findings.
- **Adaptive polling:** idle schedule sync backs off heavily; live games poll
  quickly. Keeps the project light on a shared VPS and inside free-tier API
  budgets.
- **Auth:** password-protected admin backend with separate public status
  endpoints, so the build log can be shared without exposing controls.
- **Kalshi mode:** `demo` by default. Market discovery, snapshot capture, and
  paper-trader integration are wired through `attach_real_market_context` and
  the periodic snapshot loop. WS streaming is implemented but not yet wired
  into the supervisor — it's the next step for higher-frequency snapshots.

## Strategy: Edge Registries

Both the strategy and analysis layers are built as **ordered registries of
small single-purpose modules**, so adding a hypothesis is writing one file and
appending it to a tuple — no changes to the engine.

**Soccer edges** (`src/strategy/sports/soccer/edges/`) — the active sport:

| Edge | Direction | Thesis |
|------|-----------|--------|
| `red_card_overreact` | reversion | Market overreacts to a red card; fade it. |
| `penalty_awarded` | event | A penalty is a large, mispriced probability swing. |
| `mean_reversion_favorite_trails` | reversion | When the favorite concedes, the price drops further than the true shift warrants. |
| `trend_affirm_favorite_scores` | continuation | When the favorite scores early, the market is slow to update — ride the move. |

**Analyzers** (`src/analysis/analyzers/`) — questions asked of the trade log:
`per_edge_health`, `edge_decay`, `unprofitable_edge`, `league_skew`. Each
returns findings only when a significance test crosses threshold.

## Sports Covered

NHL, NBA, MLB, NFL, Soccer, and UFC are recognized by the collectors and
classifiers. Per-sport engagement is a single source of truth — the
`sport_configs` table — with three modes:

- **active** — full ingestion, paper trades placed, strategy + findings tracked.
- **passive** — schedule + opening lines only; no live polling, no paper trades.
- **off** — not polled at all.

The bot currently runs **soccer = active** (2026 FIFA World Cup runway,
June 11 – July 19) with everything else **passive**. Flipping a sport between
modes is a database row change — no code changes required.

## Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy (async), Postgres + asyncpg
(SQLite-in-memory for tests), Alembic, structlog, scipy, pandas

**Dashboard:** React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query +
Table, Lightweight Charts, Recharts

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
| `DATABASE_URL` | Yes | Postgres DSN, e.g. `postgresql+asyncpg://lutz_bot:PASSWORD@127.0.0.1:5432/lutz_bot` |
| `ADMIN_PASSWORD_HASH` | Yes | bcrypt hash from `scripts/hash_password.py` |
| `SESSION_SECRET` | Yes | Secret for signing session cookies |
| `SCOREBOARD_LIVE_POLL_INTERVAL_S` | No | Live-game scoreboard cadence, default `10` |
| `SCOREBOARD_PREGAME_POLL_INTERVAL_S` | No | Pregame cadence, default `300` |
| `SCOREBOARD_IDLE_POLL_INTERVAL_S` | No | Idle schedule-sync cadence, default `43200` |
| `ODDS_POLL_INTERVAL_S` | No | Opening-line sync cadence, default `43200` |
| `EVENTS_POLL_INTERVAL_S` | No | Live event cadence for watched games, default `15` |
| `KALSHI_SNAPSHOT_POLL_INTERVAL_S` | No | Periodic Kalshi orderbook snapshot cadence, default `30` |

See `.env.example` for the full list including optional email notifications.

## Testing

```bash
cd backend
uv run pytest tests/ -q      # 234 tests
uv run ruff check .          # linting
uv run ruff format --check . # formatting
```

## Project Structure

```
backend/
  src/
    ingestion/     # Kalshi REST/WS, ESPN scoreboard/events, Odds API
    strategy/      # Event detector, classifier, scorer, per-sport edge registries
    paper_trader/  # Trade simulator, Kelly sizing, portfolio tracking
    analysis/      # Accumulators, analyzer registry, significance tests
    api/routes/    # REST endpoints (games, trades, analysis, config, ...)
    services/      # Trade, config, ingestion, and runtime services
    models/        # SQLAlchemy ORM (10 tables)
    core/          # Auth, DB, types, exceptions, logging
  tests/           # 234 tests across ingestion, strategy, paper trader, analysis, API
  alembic/         # Async migrations
dashboard/
  src/
    pages/         # Overview, per-Sport, Strategy, Analytics, Trades, Markets, Data, public status
    components/    # Charts (equity curve, sizing comparison, sport breakdown), UI primitives
    hooks/         # TanStack Query hooks with polling
    lib/           # Typed API client, formatters
```

## API Endpoints

The admin API is session-authenticated; public status endpoints are not.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health and data source status |
| GET | `/api/status` | Public build-log status (no auth) |
| GET | `/api/sports` | Per-sport config and engagement mode |
| GET | `/api/games` | Active games (filterable by sport/status) |
| GET | `/api/games/{id}` | Game detail with events and opening lines |
| GET | `/api/events` | Recent events (filterable by sport/type) |
| GET | `/api/trades` | Paper trade history (sortable, filterable) |
| GET | `/api/trades/active` | Open positions |
| GET | `/api/analysis/summary` | Win rate, P&L, trade counts |
| GET | `/api/analysis/equity-curve` | Cumulative P&L time series |
| GET | `/api/analysis/by-sport` | Per-sport performance breakdown |
| GET | `/api/strategy` | Live strategy catalog and market policy |
| GET | `/api/insights` | Statistical findings log |
| PATCH | `/api/config/{key}` | Update strategy parameter |

## Notes

This is a public build log as much as a trading project. Credentials stay out
of the repo (`.env` is gitignored), Kalshi key material lives outside the tree,
and the history is small, scoped commits straight off `main`.

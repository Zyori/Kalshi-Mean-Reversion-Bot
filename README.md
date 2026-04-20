# Kalshi Mean Reversion Bot

A sports prediction market trading bot that detects mean-reversion opportunities on [Kalshi](https://kalshi.com). Monitors live game events via ESPN, compares in-game price movements against pre-game sportsbook lines, and simulates paper trades with Kelly criterion sizing.

**Phase 1** — data collection, paper trading, and statistical validation. No real money is at risk.

## How It Works

```
ESPN Scoreboard → detects score changes
ESPN Events     → classifies game events (goals, TDs, red cards)
The Odds API    → captures pre-game sportsbook lines as baselines
Kalshi WS/REST  → tracks live prediction market prices
                    ↓
Strategy Engine → classifies events (reversion_candidate / structural_shift / neutral)
                → scores opportunities 0.0–1.0 (deviation × time remaining)
                    ↓
Paper Trader    → quarter-Kelly sizing with Bayesian edge shrinkage
                → slippage model (0.5% + depth adjustment)
                → tracks both Kelly-sized and flat $5 PnL
                    ↓
Analysis Engine → binomial test (win rate > 50%)
                → t-test (mean PnL > $0)
                → regime change detection (last 30 vs all-time)
                → logs insights to DB when thresholds crossed
                    ↓
Dashboard       → Markets / Trades / Analytics views
                → equity curve, Kelly comparison, sport breakdown
```

## Sports Covered

NHL, NBA, MLB, NFL, Soccer (EPL), UFC — each with sport-specific event classifiers. NHL has the richest event data (power plays, goalie pulls) and is the primary validation target.

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
| `DATABASE_URL` | No | Defaults to `sqlite+aiosqlite:///./bot.db` |

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

## License

Private — not licensed for redistribution.

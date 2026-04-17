---
title: "Phase 1: Data Collection & Paper Trading System"
type: feat
status: active
date: 2026-04-17
deepened: 2026-04-17
origin: docs/brainstorms/2026-04-17-mean-reversion-bot-brainstorm.md
---

# Phase 1: Data Collection & Paper Trading System

## Enhancement Summary

**Deepened on:** 2026-04-17
**Agents used:** 14 (architecture, security, performance, Python patterns, TypeScript, simplicity, pattern consistency, data integrity, agent-native, Kelly criterion research, Kalshi auth research, ESPN API research, React dashboard research, ESPN game events research)

### Key Improvements from Deepening

1. **Scope reduction**: Cut from 11 steps to 8, from 10 tables to 7. Eliminated premature insights workflow, notification service, and 5-sport classifier setup. Start with 1 sport end-to-end.
2. **Critical async fixes**: TaskGroup supervisor pattern, `asyncio.to_thread()` for pandas/scipy, bounded queues with backpressure.
3. **ESPN event detection upgrade**: Added `/summary` endpoint polling for game events (power plays, red cards, pitcher changes) — scoreboard alone only gives scores.
4. **Kelly criterion grounding**: Quarter-Kelly default with Bayesian edge shrinkage, available bankroll subtracts pending wagers, per-correlated-group caps.
5. **Security hardening**: `.gitignore` first, `detect-secrets` pre-commit hook, PEM outside repo tree, localhost-only API binding.
6. **Dashboard upgrade**: Lightweight Charts for equity curve, TanStack Table, `tabular-nums`, `keepPreviousData` polling pattern.
7. **Python patterns**: `Protocol` over ABC for sport classifiers, `Annotated` validators over bare `NewType`, `structlog` for structured logging, injectable probability estimator for Kelly.
8. **Architecture fixes**: Unified data flow (all collectors → queues → persistence layer), explicit config boundary (`.env` for infra, DB for strategy tunables), `services/` layer, domain-split models.

### Simplification Decisions

The simplicity reviewer argued convincingly that the original plan was ~2x the needed scope. The core question is: *can we identify mean reversion opportunities with positive expected value?* Everything that doesn't directly answer that question is deferred.

**Cut from Phase 1:**
- Notification service (email) — single operator watches dashboard
- Insights approval workflow — log findings, review manually, change config in `.env`/DB
- `change_log` table — premature without validated parameters
- 5-sport classifier setup — start with 1 sport end-to-end, add more as data validates
- Docker Compose — `uv run uvicorn` works fine for solo dev
- Portfolio constraints (per-sport allocation, per-game allocation) — paper money, keep it simple

**Kept despite simplicity concerns:**
- `insights` table (simplified to a log, no approval workflow) — we need to persist statistical findings
- Kelly criterion — core to the thesis, not premature
- Dashboard with 3 views (not 5) — Markets, Trades, Analytics. Config via `.env`. Insights via log.

---

## Overview

Build Phase 1 of a mean reversion sports trading bot: a Python backend that ingests live game data and sportsbook odds, detects game events that create mean reversion opportunities on Kalshi prediction markets, simulates paper trades with Kelly criterion sizing, and performs continuous statistical analysis — all visualized through a React/TypeScript dashboard.

This is a greenfield project. The architecture is modular and forward-looking — live trading, agent integration, and ML classification are future phases that plug into interfaces defined now but not implemented (see brainstorm: Phase roadmap).

## Problem Statement / Motivation

The previous Kalshi bot (spread scalper) proved the engineering works — 1,634 live trades, functional API integration, React dashboard — but lost money because the strategy wasn't validated before trading. 83% win rate, negative PnL. The asymmetry problem: wins captured 1-3 cents, losses ran 20-40 cents (see brainstorm: Why Mean Reversion).

This project flips the approach: prove the edge exists with data before risking capital.

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Dashboard                     │
│           (TypeScript / Vite / TailwindCSS)          │
│                                                      │
│     Markets    │   Trades    │    Analytics          │
└──────────────────────┬───────────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────┴───────────────────────────────┐
│               Python Backend (FastAPI)                │
│                                                      │
│  ┌────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ Ingestion  │  │  Strategy  │  │   Analysis    │  │
│  │            │  │   Engine   │  │    Engine     │  │
│  │ kalshi_ws  │→ │            │  │               │  │
│  │ espn_poll  │→ │ detector   │  │ accumulators  │  │
│  │ espn_events│→ │ scorer     │  │ significance  │  │
│  │ odds_poll  │→ │ classifier │  │ insights_log  │  │
│  └────────────┘  └─────┬──────┘  └───────┬───────┘  │
│                        │                  │          │
│                  ┌─────┴──────┐           │          │
│                  │   Paper    │───────────┘          │
│                  │   Trader   │                      │
│                  │            │                      │
│                  │ simulator  │  ┌─────────────────┐ │
│                  │ kelly      │  │ [Future: Live   │ │
│                  │ portfolio  │  │  Trader / Agent │ │
│                  └────────────┘  │  API]           │ │
│                                  └─────────────────┘ │
│  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │   Services   │  │    PostgreSQL (via Docker)    │  │
│  │  (biz logic) │  │    SQLite (test only)         │  │
│  └──────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Research Insights: Architecture

**TaskGroup Supervisor Pattern (architecture review):**
`asyncio.TaskGroup` propagates exceptions — if any collector task raises, the entire group cancels. Use a supervisor wrapper:

```python
async def supervised(coro_fn, name: str, restart_delay: float = 5.0):
    while True:
        try:
            await coro_fn()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"{name} crashed, restarting in {restart_delay}s")
            await asyncio.sleep(restart_delay)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with asyncio.TaskGroup() as tg:
        tg.create_task(supervised(kalshi_ws_consumer, "kalshi_ws"))
        tg.create_task(supervised(espn_poller, "espn"))
        tg.create_task(supervised(espn_events_poller, "espn_events"))
        tg.create_task(supervised(odds_poller, "odds"))
        yield
```

**Unified Data Flow (pattern review):**
All collectors emit to `asyncio.Queue` instances (bounded, maxsize=1000). A single persistence task drains queues and writes to DB. This eliminates the inconsistency where some collectors wrote directly to DB while others used queues.

**pandas/scipy Must Not Block the Event Loop (performance review):**
All statistical computation wrapped in `asyncio.to_thread()`:

```python
async def on_trade_resolved(trade: PaperTrade):
    await asyncio.to_thread(accumulators.update, trade)
    await asyncio.to_thread(significance.check_thresholds)
```

**PostgreSQL from Day One (architecture + performance reviews):**
SQLite under concurrent async writes will produce `database is locked` errors. The complexity cost of PostgreSQL via Docker is near-zero and eliminates an entire class of bugs. SQLite only for test fixtures.

**Config Boundary (pattern review):**
Two config systems exist — make the boundary explicit:
- `.env` via pydantic-settings: infrastructure (API keys, DB URL, SMTP, PEM path, server port)
- `config_params` DB table: strategy tunables (thresholds, Kelly multiplier, scoring weights)

No overlap. A parameter lives in exactly one place.

### Project Structure

```
kalshi-mean-reversion-bot/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, lifespan, supervisor
│   │   ├── config.py                # pydantic-settings for infra config
│   │   ├── ingestion/               # renamed from "collectors" for consistency
│   │   │   ├── __init__.py
│   │   │   ├── kalshi_ws.py         # Kalshi WebSocket client + auth
│   │   │   ├── kalshi_rest.py       # Kalshi REST client + auth (RSA-PSS)
│   │   │   ├── espn_scoreboard.py   # ESPN scoreboard poller (scores/state)
│   │   │   ├── espn_events.py       # ESPN summary poller (play-by-play events)
│   │   │   └── odds.py              # The Odds API poller
│   │   ├── strategy/
│   │   │   ├── __init__.py
│   │   │   ├── detector.py          # Detect game events from ESPN deltas
│   │   │   ├── scorer.py            # Score reversion opportunities
│   │   │   ├── classifier.py        # Temporary shock vs structural shift
│   │   │   └── sports/
│   │   │       ├── __init__.py
│   │   │       ├── protocols.py     # Protocol (not ABC) for sport classifiers
│   │   │       └── nhl.py           # First sport — start here
│   │   ├── paper_trader/
│   │   │   ├── __init__.py
│   │   │   ├── simulator.py         # Paper trade execution + slippage model
│   │   │   ├── kelly.py             # Kelly criterion sizing
│   │   │   └── portfolio.py         # Track simulated positions + PnL
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── accumulators.py      # Running stats per sport/event type
│   │   │   └── significance.py      # Statistical tests + insight logging
│   │   ├── services/                # Business logic orchestration
│   │   │   ├── __init__.py
│   │   │   ├── trade_service.py     # Paper trade lifecycle
│   │   │   └── config_service.py    # Strategy config CRUD + change tracking
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── markets.py
│   │   │   │   ├── events.py
│   │   │   │   ├── trades.py
│   │   │   │   ├── analysis.py
│   │   │   │   ├── config.py
│   │   │   │   └── health.py
│   │   │   └── dependencies.py
│   │   ├── models/                  # Split by domain, not single files
│   │   │   ├── __init__.py
│   │   │   ├── game.py              # Game, GameEvent ORM + schemas
│   │   │   ├── market.py            # Market, OpeningLine, Snapshot ORM + schemas
│   │   │   ├── trade.py             # PaperTrade ORM + schemas
│   │   │   ├── analysis.py          # Insight ORM + schemas
│   │   │   └── config.py            # ConfigParam ORM + schemas
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── database.py          # Async engine, sessionmaker
│   │       ├── auth.py              # Kalshi RSA-PSS signing
│   │       ├── types.py             # Annotated type validators
│   │       ├── exceptions.py        # Custom exception hierarchy
│   │       └── logging.py           # structlog configuration
│   ├── tests/
│   │   ├── conftest.py              # In-memory SQLite fixtures
│   │   ├── test_ingestion/
│   │   ├── test_strategy/
│   │   ├── test_paper_trader/
│   │   ├── test_analysis/
│   │   └── test_api/
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   └── pyproject.toml
├── dashboard/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── lib/
│   │   │   ├── api.ts               # Typed API client
│   │   │   └── utils.ts             # Formatters (currency, percent, date)
│   │   ├── components/
│   │   │   ├── ui/                   # Primitives (Card, Badge, Skeleton)
│   │   │   ├── charts/              # Chart wrappers (Lightweight Charts, Recharts)
│   │   │   └── tables/              # TanStack Table wrappers
│   │   ├── layouts/
│   │   │   └── DashboardLayout.tsx  # Sidebar + header + Outlet
│   │   ├── pages/
│   │   │   ├── MarketsPage.tsx
│   │   │   ├── TradesPage.tsx
│   │   │   └── AnalyticsPage.tsx
│   │   └── hooks/
│   │       ├── useMarkets.ts
│   │       ├── useTrades.ts
│   │       └── useAnalytics.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml          # detect-secrets hook
├── README.md
└── docs/
    ├── brainstorms/
    └── plans/
```

### Research Insights: Python Patterns

**Use `Protocol` Instead of ABC for Sport Classifiers (Python review):**

```python
from typing import Protocol

class SportClassifier(Protocol):
    def classify_event(self, event: GameEvent, game: Game) -> EventClassification: ...
    def score_opportunity(self, event: GameEvent, game: Game, baseline: float) -> float: ...
```

Any class implementing these methods satisfies the protocol without inheriting from anything. More Pythonic, more testable.

**Use `Annotated` Validators, Not Bare `NewType` (Python review):**

`NewType` provides zero runtime enforcement. `Cents(50) + Probability(0.7)` compiles and runs without error.

```python
from typing import Annotated
from pydantic import AfterValidator

def validate_cents(v: int) -> int:
    if v < 0:
        raise ValueError("Cents cannot be negative")
    return v

Cents = Annotated[int, AfterValidator(validate_cents)]
Probability = Annotated[float, AfterValidator(lambda v: v if 0.0 <= v <= 1.0 else (_ for _ in ()).throw(ValueError("Probability must be 0-1")))]
```

These validate at Pydantic boundaries (model creation, API input/output) while remaining plain `int`/`float` in business logic.

**Add `structlog` for Structured Logging (Python review):**
Async services with concurrent tasks need structured JSON logging to debug production issues. Add `structlog` to dependencies and configure in `core/logging.py`.

**Kelly Probability Estimator as Injectable (Python review):**
The `p = 0.50 + (score * 0.25)` mapping is arbitrary. Make it a `Protocol`:

```python
class ProbabilityEstimator(Protocol):
    def estimate(self, score: float, context: dict) -> float: ...

class LinearEstimator:
    def estimate(self, score: float, context: dict) -> float:
        return 0.50 + score * 0.20  # conservative default

class BayesianEstimator:  # Phase 2
    def estimate(self, score: float, context: dict) -> float: ...
```

---

### Implementation Steps

Phase 1 is broken into 8 ordered build steps (reduced from 11). Each step produces a working, testable increment.

---

#### Step 1: Project Scaffold & Infrastructure

**Goal:** Skeleton that runs — FastAPI serves health endpoint, DB connects, config loads, linting passes.

**Files:**

| File | What It Does |
|------|-------------|
| `.gitignore` | **FIRST FILE COMMITTED.** Python + Node ignores: `.venv/`, `__pycache__/`, `*.pem`, `.env`, `*.db`, `*.sqlite3`, `node_modules/`, `dist/`, `.DS_Store`, `alembic/versions/*.pyc` |
| `.pre-commit-config.yaml` | `detect-secrets` hook to catch high-entropy strings in tracked files. Prevents accidental credential commits in a public repo. |
| `backend/pyproject.toml` | Dependencies: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, aiosqlite (test only), httpx, websockets, pydantic-settings, alembic, pandas, numpy, scipy, structlog, cryptography, pytest, pytest-asyncio, respx, ruff, pyright |
| `backend/src/main.py` | FastAPI app with lifespan + supervisor pattern. Empty TaskGroup. |
| `backend/src/config.py` | pydantic-settings `BaseSettings`. Infra config from `.env`. Validates at startup. |
| `backend/src/core/database.py` | Async engine (asyncpg for PostgreSQL) + `async_sessionmaker(expire_on_commit=False)`. |
| `backend/src/core/types.py` | `Annotated` type validators: `Cents`, `Probability`, `MarketTicker`, `SportKey`. |
| `backend/src/core/exceptions.py` | Custom exception hierarchy: `IngestionError`, `StrategyError`, `TradingError`. |
| `backend/src/core/logging.py` | `structlog` configuration: JSON output, bound logger factory. |
| `backend/src/core/auth.py` | Kalshi RSA-PSS signing (see Kalshi Auth section below). |
| `backend/src/models/` | Domain-split ORM models + Pydantic schemas (see Data Model section below). |
| `backend/src/api/routes/health.py` | `/api/health` — per-source status + uptime. |
| `backend/src/api/dependencies.py` | `get_db()` async generator. |
| `backend/alembic/` | Async Alembic setup. Initial migration creates all tables. |
| `backend/tests/conftest.py` | In-memory SQLite fixtures, `httpx.AsyncClient` test client. |
| `.env.example` | All config keys with placeholder values + comments. |
| `README.md` | Project overview, setup guide, architecture diagram. |

### Research Insights: Kalshi RSA-PSS Auth (Python Port)

Port from `Kalshi-Bot/src/api/kalshi-rest.ts:67-79`. Working Python implementation:

```python
import base64
import time
import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

class KalshiAuth(httpx.Auth):
    def __init__(self, key_id: str, private_key_path: str):
        self.key_id = key_id
        with open(private_key_path, "rb") as f:
            self.private_key = serialization.load_pem_private_key(f.read(), password=None)

    def auth_flow(self, request: httpx.Request):
        timestamp_ms = str(int(time.time() * 1000))
        path = request.url.raw_path.decode("utf-8")
        message = f"{timestamp_ms}{request.method}{path}".encode("utf-8")
        signature = self.private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
        request.headers["KALSHI-ACCESS-KEY"] = self.key_id
        request.headers["KALSHI-ACCESS-SIGNATURE"] = base64.b64encode(signature).decode()
        request.headers["KALSHI-ACCESS-TIMESTAMP"] = timestamp_ms
        yield request
```

Key detail: use `raw_path` (preserves query string), not `.path`. WebSocket auth uses message format `{timestamp_ms}GET/trade-api/ws/v2`.

### Research Insights: Security (Public Repo)

| Priority | Action | Detail |
|----------|--------|--------|
| **Do first** | `.gitignore` before any other file | A single `git add .` before creating it permanently leaks secrets |
| **Do first** | `detect-secrets` pre-commit hook | Catches high-entropy strings in tracked files |
| **Critical** | PEM outside repo tree | Store at `~/.config/kalshi/private_key.pem`, reference via env var `KALSHI_PRIVATE_KEY_PATH` |
| **Critical** | Bind API to localhost | `uvicorn --host 127.0.0.1`. All mutating endpoints are unauthenticated — fine for localhost, dangerous if exposed. |
| **High** | Explicit CORS origins | Pin to `http://localhost:5173` in dev. Never wildcard. |
| **High** | Whitelist sort/filter columns | Never pass raw query params to `.order_by()`. |
| **Medium** | Non-root Docker user | When Docker is added later. |
| **Medium** | GitHub secret scanning | Enable on the repo. |

**Acceptance Criteria:**
- [ ] `.gitignore` is the first committed file in repo history
- [ ] `detect-secrets` pre-commit hook installed and passing
- [ ] `uv sync` installs all dependencies
- [ ] `uv run uvicorn backend.src.main:app --host 127.0.0.1` starts and serves `/api/health`
- [ ] `uv run alembic upgrade head` creates all tables in PostgreSQL
- [ ] `uv run pytest` passes with health endpoint test
- [ ] `ruff check` and `ruff format --check` pass
- [ ] `structlog` producing JSON output

---

#### Step 2: Data Ingestion — Kalshi

**Goal:** Connect to Kalshi WebSocket and REST API. Stream market data to a bounded queue.

**Files:**

| File | What It Does |
|------|-------------|
| `backend/src/ingestion/kalshi_rest.py` | Async REST client using `httpx` + `KalshiAuth`. Methods: `get_markets()`, `get_orderbook(ticker)`, `get_event(event_ticker)`. Token bucket rate limiter. |
| `backend/src/ingestion/kalshi_ws.py` | Async WebSocket client using `websockets`. Auth handshake. Subscribe to orderbook channels. Parse messages with Pydantic. Reconnect with exponential backoff (1s base, 30s max). On any sequence gap: request full snapshot. Emit to bounded `asyncio.Queue(maxsize=1000)`. |

**Reconnection and Staleness Spec:**
- Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s max. Unlimited retries (via supervisor).
- On any sequence gap > 0: log warning via `structlog`, request full orderbook snapshot.
- Staleness: no message for 30s → mark `stale`. Health endpoint reflects state.
- During `stale` or `disconnected`: paper trader pauses new entries for affected markets.

**Research Insights: Queue Backpressure (performance review):**
Unbounded queues are a memory leak under burst conditions. All queues use `maxsize=1000`. If a queue is full, the producer logs a warning and drops the oldest item (not blocks — blocking a WebSocket consumer causes reconnection cascades).

**Testing Note (Python review):**
`respx` cannot mock WebSockets. Use `pytest-mock` with manual async context manager mocking for WebSocket tests. `respx` is correct for REST client tests.

**Acceptance Criteria:**
- [ ] Connects to Kalshi demo WebSocket with valid RSA-PSS auth
- [ ] Parses orderbook updates into Pydantic models
- [ ] Reconnects automatically via supervisor after disconnect
- [ ] Emits to bounded queue; drops oldest on overflow with log warning
- [ ] Health endpoint shows Kalshi connection status
- [ ] REST tests use `respx`; WebSocket tests use `pytest-mock`

---

#### Step 3: Data Ingestion — ESPN + The Odds API

**Goal:** Poll ESPN for scores AND game events. Poll The Odds API for sportsbook lines.

**Files:**

| File | What It Does |
|------|-------------|
| `backend/src/ingestion/espn_scoreboard.py` | Polls ESPN scoreboard API per sport (10s interval). Parses score, period, clock, status. Detects **score deltas** between polls. Emits `GameStateUpdate` to queue. |
| `backend/src/ingestion/espn_events.py` | **NEW: Not in original plan.** Polls ESPN `/summary?event={id}` endpoint for active games where we need event-level data. Diffs play-by-play array between polls. Emits `GameEvent` objects (power plays, red cards, pitcher changes, penalty situations). One request per game, not per sport. |
| `backend/src/ingestion/odds.py` | Polls The Odds API for pre-game lines. Captures opening lines early and stores them. Maps American odds to implied probability. 300s interval pre-game, stops once game starts. |

### Research Insights: ESPN API (ESPN research)

**Scoreboard endpoints (battle-tested in old bot):**

| Sport | Endpoint |
|-------|----------|
| NHL | `site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard` |
| NBA | `.../basketball/nba/scoreboard` |
| MLB | `.../baseball/mlb/scoreboard` |
| NFL | `.../football/nfl/scoreboard` |
| Soccer | `.../soccer/{league}/scoreboard` (eng.1, usa.1, uefa.champions) |

**The critical gap: scoreboard doesn't have game events.**
Scoreboard gives scores, period, clock, and game state. It does NOT give power plays, red cards, pitcher changes, or any in-game event detail.

**Solution: ESPN Summary endpoint.**
`site.web.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={eventId}`

This returns play-by-play data with event types. NHL plays include penalty types and power play indicators. Soccer `details[]` contains card events (available in scoreboard too). MLB plays include pitching changes. This is a per-game request (heavier) but necessary for mean reversion signal detection.

**Architecture:**
- `espn_scoreboard.py`: polls once per sport per interval → detects score changes, game state transitions
- `espn_events.py`: polls per-game summary for games the strategy engine is actively watching → detects specific events (power plays, cards, pitcher changes)

Only poll summary for games where: (a) game is live AND (b) the game has a paper trade or is flagged as a potential opportunity. This keeps request volume manageable.

**ESPN Latency Handling:**
ESPN data arrives 15-45 seconds after real-world events. Every `GameEvent` carries:
- `detected_at`: when ESPN reported it (when we polled and saw the change)
- `estimated_real_at`: `detected_at - sport_latency_estimate` (15s NHL/NBA, 20s soccer, 10s MLB)

Paper trade entries use the Kalshi price at `detected_at` — the price when *we* learned about the event. This is realistic. The analysis engine separately tracks `price_at_detection` vs `price_at_estimated_event_time` to measure latency cost.

**Source Disagreement:**
If ESPN and The Odds API opening lines differ by > 5 percentage points implied probability: flag as `disputed_baseline`, log both, use average, tag paper trades for separate analysis.

**Acceptance Criteria:**
- [ ] Scoreboard poller detects score changes between polls
- [ ] Events poller detects power play starts in NHL summary data
- [ ] The Odds API captures opening lines and persists them
- [ ] Both pollers handle HTTP errors with retry backoff (don't crash via supervisor)
- [ ] Health endpoint shows ESPN/Odds status + last successful poll timestamp
- [ ] All events carry `detected_at` and `estimated_real_at` timestamps
- [ ] Tests use `respx` for HTTP mocking

---

#### Step 4: Data Model & Persistence

**Goal:** Database schema, migrations, domain-split models.

**7 tables (reduced from 10):**

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│     games       │     │    markets       │     │  opening_lines  │
├─────────────────┤     ├──────────────────┤     ├─────────────────┤
│ id (PK)         │──┐  │ id (PK)          │  ┌──│ id (PK)         │
│ sport           │  │  │ game_id (FK)     │──┘  │ game_id (FK)    │
│ home_team       │  └──│ kalshi_ticker    │     │ source          │
│ away_team       │     │ market_type      │     │ home_prob       │
│ start_time      │     │ opened_at        │     │ away_prob       │
│ espn_id (idx)   │     │ resolved_at      │     │ captured_at     │
│ status          │     │ resolution       │     │ odds_raw (JSON) │
│ opening_line_   │     └──────────────────┘     └─────────────────┘
│   home_prob     │
│ opening_line_   │     ┌──────────────────┐
│   source        │     │   game_events    │
└─────────────────┘     ├──────────────────┤
                        │ id (PK)          │
┌──────────────────┐    │ game_id (FK,idx) │
│  paper_trades    │    │ event_type       │
├──────────────────┤    │ description      │
│ id (PK)          │    │ home_score       │
│ game_event_id(FK)│    │ away_score       │
│ market_id (FK)   │    │ period           │
│ sport (idx)      │    │ clock            │
│ side             │    │ detected_at (idx)│
│ entry_price      │    │ estimated_real_at│
│ entry_price_adj  │    │ espn_data (JSON) │
│ slippage_cents   │    │ classification   │
│ confidence_score │    │ confidence_score │
│ kelly_fraction   │    │ kalshi_price_at  │
│ kelly_size_cents │    │ baseline_prob    │
│ exit_price       │    │ deviation        │
│ pnl_cents        │    └──────────────────┘
│ pnl_kelly_cents  │
│ status (idx)     │    ┌──────────────────┐
│ entered_at (idx) │    │   insights       │
│ resolved_at      │    ├──────────────────┤
│ resolution       │    │ id (PK)          │
│ game_context JSON│    │ type             │
│ reasoning (JSON) │    │ title            │
│ skip_reason      │    │ body             │
└──────────────────┘    │ data (JSON)      │
                        │ confidence       │
┌──────────────────┐    │ recommendation   │
│   snapshots      │    │ status           │
├──────────────────┤    │ created_at       │
│ id (PK)          │    └──────────────────┘
│ market_id(FK,idx)│
│ kalshi_bid       │    ┌──────────────────┐
│ kalshi_ask       │    │  config_params   │
│ kalshi_volume    │    ├──────────────────┤
│ bid_depth        │    │ key (PK)         │
│ ask_depth        │    │ value            │
│ captured_at (idx)│    │ type             │
└──────────────────┘    │ description      │
                        │ updated_at       │
                        └──────────────────┘
```

**Key changes from original plan:**
- `opportunities` table eliminated — fields folded into `game_events` (classification, confidence, kalshi_price, baseline_prob, deviation) and `paper_trades` (confidence_score, reasoning JSON)
- `change_log` table eliminated — defer to Phase 2 when parameters are validated
- `paper_trades.reasoning` added as structured JSON (agent-native review: agents need to see scoring rationale)
- Explicit indexes on: `game_events(game_id)`, `game_events(detected_at)`, `paper_trades(sport)`, `paper_trades(status)`, `paper_trades(entered_at)`, `snapshots(market_id, captured_at)`

**Slippage Model:**
1. `entry_price` = Kalshi best ask at detection time (we're buying)
2. `entry_price_adj` = entry_price + slippage
3. Slippage: `max(1 cent, 0.5% of entry_price)`
4. If orderbook depth at best ask < 10 contracts: +1 cent per 5 contracts of shortfall
5. Both raw and adjusted PnL tracked. `slippage_cents` recorded for transparency.

**Snapshot Retention (performance review):**
Snapshots table will grow at ~100K+ rows/hour with 50 markets. Add:
- Composite index on `(market_id, captured_at)`
- Retention: downsample to 1-minute intervals after 24h, delete raw after 7d
- Implement via a periodic cleanup task in the supervisor

**Market Closure / Early Settlement:**
- Early settlement: mark as `settled_early`, record final price, flag in statistics
- Resolution unavailable: mark as `unresolved`, exclude from PnL statistics

**Acceptance Criteria:**
- [ ] All tables created via Alembic migration with explicit indexes
- [ ] Domain-split Pydantic schemas validate all inputs/outputs
- [ ] `Annotated` type validators used for Cents, Probability at model boundaries
- [ ] Snapshot retention task runs periodically
- [ ] Tests verify model creation, relationships, constraints

---

#### Step 5: Strategy Engine — Event Detection & Scoring

**Goal:** Detect game events, classify them, score opportunities. Start with ONE sport (NHL).

**Files:**

| File | What It Does |
|------|-------------|
| `backend/src/strategy/detector.py` | Consumes events from ESPN queues. Detects meaningful events: score changes, period transitions, power plays (from summary data). Correlates with Kalshi price at detection time. |
| `backend/src/strategy/classifier.py` | Classifies events as `reversion_candidate`, `structural_shift`, or `neutral`. Delegates to sport-specific classifiers via Protocol. |
| `backend/src/strategy/scorer.py` | Scores reversion candidates 0.0-1.0. Simple formula (not over-engineered). |
| `backend/src/strategy/sports/protocols.py` | `SportClassifier` Protocol definition. |
| `backend/src/strategy/sports/nhl.py` | First sport implementation. |

### Research Insights: Start With One Sport (Simplicity Review)

Build the entire pipeline end-to-end for NHL first. The abstract classifier pattern exists (Protocol), but only one implementation ships. Add more sports when data validates the approach. This is not laziness — it's discipline.

**NHL Classifier (Phase 1):**

| Classification | Trigger | Parameters |
|----------------|---------|------------|
| `reversion_candidate` | Power play goal against favorite (period 1-2, pre-game line > 60%) | `min_favorite_prob: 0.60` |
| `reversion_candidate` | Even-strength goal against favorite (period 1, pre-game line > 65%) | `min_favorite_prob: 0.65` |
| `structural_shift` | Star goalie pulled | N/A |
| `structural_shift` | 3+ goal deficit after period 2 | `max_deficit_reversion: 2` |
| `neutral` | Everything else | |

All thresholds stored in `config_params` DB table.

**Scoring Formula (simplified from 5 weights to 2 factors):**

```python
score = (
    0.6 * normalize(deviation_from_baseline, 0.05, 0.30) +
    0.4 * normalize(time_remaining_pct, 0.25, 0.90)
)
```

Two factors: how far has the price deviated from the sportsbook line, and how much game time remains. Start simple. The data will tell us if more factors matter. Weights stored in `config_params`.

**Acceptance Criteria:**
- [ ] Event detector identifies score changes and power play events from ESPN data
- [ ] NHL classifier categorizes events into three buckets
- [ ] Scorer produces 0.0-1.0 confidence for reversion candidates
- [ ] Structural shifts logged but do not generate paper trades
- [ ] All thresholds configurable via `config_params`
- [ ] Tests cover NHL classifier with realistic game scenarios

---

#### Step 6: Paper Trader — Simulation & Kelly Sizing

**Goal:** Simulate trades with Kelly criterion. Track portfolio.

### Research Insights: Kelly Criterion (Kelly research)

**Quarter-Kelly, not half-Kelly.** Full Kelly maximizes log-wealth growth but produces 50%+ drawdowns. Half-Kelly gives 75% of growth with less variance. Quarter-Kelly is the practitioner standard for models with uncertain probability estimates — which is exactly our situation with zero empirical backing.

**Bayesian edge shrinkage.** The plan's `p = 0.50 + (score * 0.25)` is an arbitrary linear function. Better approach:

```python
class ConservativeEstimator:
    def estimate(self, score: float, context: dict) -> float:
        raw_edge = score * 0.20  # max 20% estimated edge
        shrinkage = 0.5  # discount factor for uncertainty
        return 0.50 + raw_edge * shrinkage
```

This gives max estimated p = 0.60 (not 0.75). Deliberately conservative until data validates calibration.

**Available bankroll must subtract pending wagers.**
If you have 3 open positions totaling $30, bankroll for the 4th bet is `bankroll - $30`, not `bankroll`.

**Correlated bet cap.**
Same-sport, same-day bets are correlated. Cap total exposure per correlated group at 1.5x a single max Kelly bet.

**Track Kelly vs flat betting in parallel.**
Record both Kelly-sized and flat-sized ($5) hypothetical PnL for every trade. This produces a direct comparison chart showing whether Kelly adds value.

**Implementation pitfalls to avoid:**
- If Kelly fraction ≤ 0, do not trade (no edge). Never place a minimum bet.
- Always floor bet size, never ceil.
- Recalculate bankroll after every resolved bet, not once per day.
- Track calibration: binned predicted probability vs actual win rate.

**Kelly Spec:**

```python
fraction_multiplier = 0.25  # quarter-Kelly (configurable)
min_bet = 100  # $1.00 in cents
max_bet = 2500  # $25.00 in cents

def kelly_size(p: float, entry_price_cents: int, bankroll_cents: int, pending_wagers_cents: int) -> int:
    b = (100 - entry_price_cents) / entry_price_cents  # payout ratio
    f = (b * p - (1 - p)) / b  # Kelly fraction
    if f <= 0:
        return 0  # no edge
    available = bankroll_cents - pending_wagers_cents
    size = int(f * fraction_multiplier * available)  # floor, not ceil
    return max(min(size, max_bet), min_bet) if size >= min_bet else 0
```

**Portfolio Constraints (simplified):**
- Max concurrent positions: 15 (configurable)
- Paper bankroll: $500 (configurable), tracks as if real
- Recalculate bankroll after every resolution

**Acceptance Criteria:**
- [ ] Kelly correctly calculates fraction (verified against hand calculations)
- [ ] Quarter-Kelly is default with configurable multiplier
- [ ] Available bankroll subtracts pending wagers
- [ ] Kelly fraction ≤ 0 results in no trade (never minimum bet)
- [ ] Both Kelly-sized and flat-sized PnL tracked per trade
- [ ] Tests verify Kelly math including edge cases (f ≤ 0, bankroll exhausted)

---

#### Step 7: Analysis Engine — Statistics & Insight Logging

**Goal:** Continuous statistical analysis. Log findings when significant.

**Files:**

| File | What It Does |
|------|-------------|
| `backend/src/analysis/accumulators.py` | Running statistics per: sport, event type, score bucket. Tracks: count, win rate, mean PnL, std dev. Updates after every trade resolution via `asyncio.to_thread()`. |
| `backend/src/analysis/significance.py` | Statistical tests + insight logging. Binomial test for win rate. T-test for mean PnL. Minimum sample gates. Recency weighting. Writes to `insights` table when thresholds crossed. |

**Statistical Spec:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Minimum sample size | 30 trades | Below this, variance dominates |
| Significance level (alpha) | 0.05 | Two-tailed |
| Win rate test | Binomial, H0: p=0.50 | Better than coin flip? |
| PnL test | One-sample t-test, H0: mean=0 | Mean PnL positive? |
| Recency window | Last 100 trades or 30 days, whichever smaller | Prevents stale data dominating |
| Regime change | Last-30 win rate vs all-time, delta > 15pp AND n≥20 | Catches real shifts |
| Edge validated | Win rate p < 0.05 AND mean PnL > 0 AND n ≥ 30 | Conservative triple-gate |

**Insight Types (logged to DB, no approval workflow):**
1. `edge_validated`: "NHL PP reversion: 47 obs, 68% win rate (p=0.02), mean +$2.30/trade"
2. `edge_degraded`: "Win rate dropped from 65% to 48% over last 30 trades"
3. `parameter_recommendation`: "Trades entering at 10+ point leads win at 72% vs 54% for 8-9"
4. `anomaly_detected`: "Reversion rate is 3.2 SD below running mean over last 2 weeks"

Phase 1: insights are logged and displayed on the dashboard. Human reviews and manually changes config. Phase 2 adds the approval workflow.

### Research Insights: Performance

**All pandas/scipy in `asyncio.to_thread()` (performance review):**
Statistical tests are CPU-bound and will block the event loop for 10-500ms. Non-negotiable — wrap every call.

**Bound accumulator data structures (performance review):**
5 sports × 10 event types × 10 score buckets = 500 accumulator instances, each holding history arrays. Use fixed-size rolling windows (max 100 trades per accumulator). This is a hard cap on stored data, not just a query window.

**Acceptance Criteria:**
- [ ] Accumulators update incrementally via `asyncio.to_thread()`
- [ ] Binomial and t-tests produce correct p-values (verified against scipy reference)
- [ ] Insights only generated when minimum sample size met
- [ ] Accumulator data structures bounded to 100 items per bucket
- [ ] Tests verify statistical calculations with known datasets

---

#### Step 8: API Layer + Dashboard

**Goal:** Complete REST API. React dashboard with 3 views.

**API Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Per-source status + uptime |
| GET | `/api/games` | Active games with odds comparison |
| GET | `/api/games/{game_id}` | Single game with events |
| GET | `/api/games/{game_id}/events` | Events for a game |
| GET | `/api/events` | Recent events, filterable by sport/type |
| GET | `/api/trades` | Paper trade history, filterable/sortable |
| GET | `/api/trades/active` | Open positions |
| GET | `/api/trades/{id}` | Trade detail with `reasoning` JSON |
| GET | `/api/analysis/summary` | Overall stats |
| GET | `/api/analysis/by-sport` | Sport breakdown |
| GET | `/api/analysis/by-event-type` | Event type breakdown |
| GET | `/api/analysis/equity-curve` | Time-series PnL (Recharts data) |
| GET | `/api/analysis/kelly-comparison` | Kelly vs flat sizing comparison |
| GET | `/api/insights` | Insight log |
| GET | `/api/config` | All strategy parameters |
| PATCH | `/api/config/{key}` | Update parameter (via `config_service`) |

**API Design Fixes (pattern + agent-native reviews):**
- Games and events use proper nested resources (`/api/games/{id}/events`)
- `trades/{id}` response includes structured `reasoning` field (not just raw JSON)
- `PATCH /api/config/{key}` accepts body with `value` + `reason` fields — logs the change
- All sort/filter columns whitelisted explicitly (security review)

### Research Insights: Dashboard (React research)

**3 views, not 5.** Ship polished: Markets, Trades, Analytics. Config is done via `.env` + API. Insights displayed in Analytics view.

**Lightweight Charts for equity curve.** TradingView's Lightweight Charts (45KB, WebGL) instantly signals domain knowledge. Use for the main equity curve. Recharts for bar charts, histograms.

**TanStack Table for trades.** Sortable, filterable, paginated. Demonstrates you can handle a real table library. Right-align all numeric columns.

**Critical CSS details:**
- `font-variant-numeric: tabular-nums` on ALL numbers
- Near-black base (`#0a0a0f`), card surfaces at `#12131a`)
- Green `#22c55e` for profit, red `#ef4444` for loss
- Monospace font for financial data (JetBrains Mono)

**TanStack Query polling pattern:**

```typescript
const { data, dataUpdatedAt } = useQuery({
  queryKey: ['trades', 'active'],
  queryFn: fetchActiveTrades,
  refetchInterval: 5_000,
  staleTime: 4_000,
  placeholderData: keepPreviousData, // prevents flash on refetch
});
```

`keepPreviousData` is critical — prevents UI flash on every 5-second refetch. Show "last updated" timestamp, not loading spinners.

**Libraries:**

```bash
npm install lightweight-charts recharts @tanstack/react-query @tanstack/react-table react-router
```

**Acceptance Criteria:**
- [ ] All API endpoints return typed JSON responses
- [ ] OpenAPI docs render at `/docs`
- [ ] Filtering/pagination on list endpoints with whitelisted columns
- [ ] Dashboard Markets view shows active games with odds deviation
- [ ] Dashboard Trades view shows paper trades with sortable TanStack Table
- [ ] Dashboard Analytics view shows equity curve (Lightweight Charts) + win rate charts (Recharts) + Kelly comparison
- [ ] `tabular-nums` on all numeric displays
- [ ] `keepPreviousData` polling with "last updated" timestamp
- [ ] Vite proxy configured for backend API

---

## System-Wide Impact

### Interaction Graph

ESPN scoreboard poller detects score change → emits `GameStateUpdate` to queue → if game is interesting, ESPN events poller starts polling summary → detects power play / card / pitcher change → emits `GameEvent` to queue → detector consumes and enriches with Kalshi price → classifier categorizes (via NHL Protocol impl) → if `reversion_candidate`: scorer produces confidence → paper trader evaluates Kelly sizing and portfolio constraints → if entry: service writes `paper_trade` to DB via `trade_service` → on resolution: analysis engine updates accumulators via `asyncio.to_thread()` → if threshold crossed: writes `insight` to DB.

Config change (via API) → `config_service` validates, updates `config_params` table, invalidates in-memory cache.

### Error Propagation

- Collector crashes: supervisor restarts with backoff. Health endpoint updates. Paper trader pauses new entries.
- Queue overflow: producer drops oldest item with `structlog` warning. Never blocks.
- Database errors: service layer handles. Transient errors retried. Persistent errors surface in health endpoint.
- Analysis errors: caught per-accumulator in `to_thread()`, logged, does not block trade resolution.
- All errors use custom exceptions from `core/exceptions.py`.

### Concurrency Limits

- Max WebSocket subscriptions: 50 markets (configurable). Prioritize: active positions > higher deviation > closer to start.
- ESPN scoreboard: 1 request per sport per 10s interval. ~30 req/min across 5 sports.
- ESPN summary: 1 request per watched game per 15s. Only for games with active interest.
- The Odds API: budget 400/500 free monthly requests. Plan to upgrade to $20/month.
- Analysis: runs in thread pool, naturally queued by asyncio.
- Config cache: in-memory with write-through invalidation (not DB read per evaluation cycle).

## Acceptance Criteria

### Functional Requirements
- [ ] System connects to Kalshi, ESPN (scoreboard + summary), and The Odds API simultaneously
- [ ] Detects live game events including power plays (NHL) from ESPN summary endpoint
- [ ] Scores reversion opportunities and simulates paper trades
- [ ] Kelly criterion with quarter-Kelly default, tracks Kelly vs flat sizing
- [ ] Tracks paper trade PnL with slippage adjustment
- [ ] Runs statistical analysis after resolution (via thread pool)
- [ ] Logs insights when statistical thresholds crossed
- [ ] Dashboard displays markets, trades, and analytics
- [ ] Config changes via API persist and invalidate cache

### Non-Functional Requirements
- [ ] Backend starts in < 5 seconds
- [ ] API response time < 200ms
- [ ] System runs 24+ hours without memory leaks (bounded accumulators, snapshot retention)
- [ ] All configuration via environment variables (no hardcoded secrets)
- [ ] Public repo safe: no secrets in git history

### Quality Gates
- [ ] 80%+ test coverage on backend; 90%+ on strategy and analysis
- [ ] All Pydantic models validated at boundaries
- [ ] `ruff check` + `pyright` pass with zero errors
- [ ] TypeScript strict mode, zero errors
- [ ] OpenAPI docs complete

## Dependencies & Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ESPN API changes or blocks | Medium | High | Stable for years. Monitor 429s. Abstract data layer for swap. |
| Odds API free tier insufficient | High | Medium | Budget $20/month upgrade. 500 free requests lasts ~13 days. |
| ESPN summary endpoint lacks event detail for some sports | Medium | Medium | Start with NHL (best event data). Validate per-sport before adding. |
| ESPN latency means events arrive after prices move | High | Medium | Track latency explicitly. Edge may be smaller but still positive. |
| Paper PnL overstates real performance | Medium | High | Slippage model + dual PnL tracking (raw vs adjusted). |
| Kelly miscalibration amplifies errors | Medium | High | Quarter-Kelly + Bayesian shrinkage + flat-sizing comparison. |
| PostgreSQL adds dev complexity | Low | Low | Docker one-liner. Eliminates SQLite concurrency bugs. |

## Future Considerations

Architecture decisions that keep future phases cheap:

1. **More sports**: Add a new file in `strategy/sports/`, implement the `SportClassifier` Protocol, register it. Zero changes to core.
2. **Live trading (Phase 3)**: `paper_trader/simulator.py` interface is what a live trader implements. Swap simulation for Kalshi order placement.
3. **Agent integration (Phase 4)**: Every action available via REST API. Add optional request body to insight accept/reject for agent overrides. Define `NotificationChannel` Protocol in notifications module for future webhook support.
4. **ML classification (Phase 2)**: `classifier.py` delegates to Protocol. Swap rules for trained model. `ProbabilityEstimator` Protocol for Kelly.
5. **Insights approval workflow (Phase 2)**: `insights` table already exists. Add `change_log` table, approval endpoints, dashboard view when parameters are validated enough to warrant formal change tracking.
6. **Backtesting (Phase 2)**: All data in DB with timestamps. Replay historical events through strategy engine.

## Sources & References

### Origin

**Brainstorm document:** [docs/brainstorms/2026-04-17-mean-reversion-bot-brainstorm.md](../brainstorms/2026-04-17-mean-reversion-bot-brainstorm.md)

Key decisions carried forward:
- Event-driven entries, not price-driven (brainstorm: Entry Logic)
- Ride to resolution by default (brainstorm: Exit Logic)
- Advisory self-learning with human approval (brainstorm: Self-Learning Loop)
- Sport-agnostic architecture with priority on soccer/MLB (brainstorm: Sport Strategy)
- Kelly criterion for position sizing (brainstorm: Position Sizing)
- Dashboard with insights feed (brainstorm: architecture discussion)

### Internal References

- Kalshi RSA-PSS auth: `Kalshi-Bot/src/api/kalshi-rest.ts:67-79`
- Kalshi WebSocket auth: `Kalshi-Bot/src/api/kalshi-ws.ts:54-63`
- Kalshi wire format: `Kalshi-Bot/src/api/schemas.ts`
- ESPN endpoints: `Kalshi-Bot/src/api/espn-game-clock.ts:29-38`
- ESPN summary endpoint: `site.web.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={eventId}`
- Pydantic models: `kalshi-trade-analytics/src/models.py`
- Risk controls: `Kalshi-Bot/src/risk/risk-manager.ts`

### External References

- The Odds API: https://the-odds-api.com
- ESPN Public API reference: https://github.com/pseudo-r/Public-ESPN-API
- Lightweight Charts: https://tradingview.github.io/lightweight-charts/
- Kelly criterion mathematics: Kelly 1956, Thorp, Poundstone
- Python `cryptography` RSA-PSS: https://cryptography.io

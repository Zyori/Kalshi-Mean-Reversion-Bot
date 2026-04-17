---
date: 2026-04-17
topic: mean-reversion-bot
---

# Mean Reversion Trading Bot — Design

## What We're Building

A data-first sports trading system that identifies mean reversion opportunities on Kalshi prediction markets. The bot watches live sporting events for moments where underdogs score early or situational events (power plays, penalty kicks, turnovers) temporarily inflate underdog odds beyond what the pre-game fundamentals justify. It paper trades these opportunities, collects rich contextual data, and performs continuous statistical analysis to validate and refine the strategy over time.

The system compares professional sportsbook opening lines (the "true" pre-game probability) against Kalshi's live prices (driven by retail traders who overreact to game events) to identify positive expected value entries on favorites whose odds have been temporarily depressed.

This is Phase 1 of a multi-phase project. Live trading, autonomous agent integration, and ML-driven event classification are future modules that the architecture anticipates but does not implement.

## Why This Approach

### Approaches Considered

1. **Live trading from day one** — Rejected. The previous bot (Kalshi-Bot) proved the mechanics work (1,634 trades, functional API integration) but lost money because the strategy wasn't validated. This time: prove the edge first, trade second.

2. **Price-movement-based entry** — Rejected. Watching Kalshi price drops in isolation is noise. Kalshi is retail-driven and often mispriced even pre-game. Entry signals must be tied to real-world game events that we can reason about.

3. **Event-driven analysis with paper trading** — Selected. The core thesis is that professional sportsbook lines represent the true pre-game probability, and live game events cause Kalshi retail traders to overreact. By watching games and logging every potential opportunity with full context, we build the dataset that tells us whether this edge exists, how large it is, and under what conditions it holds.

### Why Mean Reversion

Spread scalping (the previous bot's strategy) had an 83% win rate but negative PnL because of asymmetric payoffs — wins captured 1-3 cents, losses ran 20-40 cents. Mean reversion flips this dynamic: entries are on favorites at depressed prices with significant upside when the mean reverts, and the loss case (the favorite actually loses) is bounded by the entry price. Kelly criterion sizing further optimizes the risk/reward ratio.

## Architecture

### Two-Service Design

```
┌─────────────────────────────────────────────────┐
│                 React Dashboard                  │
│         (TypeScript / Vite / TailwindCSS)        │
│                                                  │
│  Live Markets │ Paper Trades │ Insights │ Config │
└──────────────────────┬──────────────────────────┘
                       │ REST API
┌──────────────────────┴──────────────────────────┐
│                  Python Backend                   │
│              (FastAPI / asyncio)                  │
│                                                  │
│  ┌───────────┐ ┌───────────┐ ┌───────────────┐  │
│  │   Data    │ │  Strategy │ │   Analysis    │  │
│  │  Ingestion│ │   Engine  │ │    Engine     │  │
│  └───────────┘ └───────────┘ └───────────────┘  │
│  ┌───────────┐ ┌───────────┐ ┌───────────────┐  │
│  │   Paper   │ │  Insights │ │  [Future:     │  │
│  │  Trader   │ │  Generator│ │  Live Trader] │  │
│  └───────────┘ └───────────┘ └───────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │           PostgreSQL / SQLite            │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

### Python Backend Modules

| Module | Responsibility | Phase |
|--------|---------------|-------|
| **Data Ingestion** | Kalshi WebSocket/REST, ESPN API, sportsbook odds API. Normalizes all data into a unified event stream. | 1 |
| **Strategy Engine** | Event detection, opportunity scoring, entry/exit signal generation. Sport-agnostic core with sport-specific classifiers. | 1 |
| **Paper Trader** | Simulates trades against real market data. Logs entry price, trigger event, resolution, PnL. Tracks portfolio with Kelly sizing. | 1 |
| **Analysis Engine** | Running statistical accumulators. Win rates, EV calculations, confidence intervals, significance tests, trend detection. | 1 |
| **Insights Generator** | Threshold-driven analysis that surfaces findings when data crosses statistical significance. Writes recommendations to the insights feed. | 1 |
| **Notification Service** | Email alerts for high-signal insights. Simple SMTP, threshold-triggered, not scheduled. | 1 |
| **Live Trader** | Kalshi order placement, position management, exit logic. Placeholder interface defined in Phase 1, implemented later. | Future |
| **Agent API** | Endpoints for external LLM/agent integration. Read insights, approve changes, query analysis. Interface defined in Phase 1, implemented later. | Future |

### TypeScript Dashboard

| View | Purpose | Phase |
|------|---------|-------|
| **Live Markets** | Currently watched games, real-time odds comparison (sportsbook vs Kalshi), detected events | 1 |
| **Paper Trades** | Active and resolved simulated trades, entry/exit details, PnL | 1 |
| **Analytics** | Equity curves, win rates by sport/event type, Kelly performance, distributions | 1 |
| **Insights Feed** | Proactive findings from the analysis engine, with Accept/Reject/Discuss actions | 1 |
| **Change Log** | Timestamped record of strategy changes with before/after performance tracking | 1 |
| **Config** | Strategy parameters, sport toggles, threshold settings | 1 |
| **Live Trading** | Real trade management, positions, balances. Grayed out placeholder in Phase 1. | Future |

### REST API Design Principles

Every piece of data and every action is exposed through the API. The dashboard is one consumer. Future agents are another. The API is the integration point, not the dashboard.

Key endpoint groups:
- `/api/markets` — live market state, odds comparisons
- `/api/events` — detected game events and their classifications
- `/api/trades` — paper trade history and active positions
- `/api/analysis` — statistical summaries, breakdowns by sport/event type
- `/api/insights` — findings feed, approval workflow, change log
- `/api/config` — strategy parameters (read and write)
- `/api/health` — system status

## Key Decisions

### Data Sources
- **ESPN API** as primary source for live game state and pre-game context (battle-tested in previous bot)
- **+1 sportsbook API** (DraftKings or FanDuel, whichever has best free access) for opening odds baseline
- **Flag discrepancies** between ESPN and sportsbook odds — don't blindly trust a single source
- **Kalshi** is the trading venue, not the odds oracle. Kalshi pre-game lines are retail-driven and unreliable. Sportsbooks are the professionals.

### Sport Strategy
- Architecture is sport-agnostic — sport-specific logic lives in pluggable classifier modules
- **Priority sports for data collection:**
  - Soccer (World Cup June-July 2026 — high volume validation window)
  - MLB (season just started, daily games through October)
  - NBA/NHL playoffs (happening now, collect while available)
- Each sport has different reversion dynamics and event types
- UFC and golf are stretch goals — high variance and non-head-to-head formats may not fit the thesis

### Mean Reversion Event Archetypes

| Sport | Trigger Event | Why It Reverts |
|-------|--------------|----------------|
| Hockey | Power play goal against favorite | Situational advantage, not skill gap |
| Soccer | Penalty kick / early underdog goal | Set piece luck, not sustained dominance |
| NFL | Pick-six / kickoff return TD | Freak play, doesn't reflect team quality |
| NBA | Underdog hot start / big Q1 lead | Regression to shooting averages |
| MLB | Early-inning rally against ace pitcher | Small sample, pitcher settles in |

### What Is NOT a Mean Reversion Opportunity (Structural Shifts)
- Red card to the favorite (permanent disadvantage — possibly bet the other way)
- Star player injury / ejection
- Starting pitcher pulled early in MLB
- Key player foul trouble in basketball

The system must learn to distinguish temporary shocks from structural shifts. Initially this is rule-based; long-term this is the ML classification problem.

### Entry Logic
- **Event-driven, not price-driven.** A Kalshi price drop alone is not an entry signal. A real-world game event that caused the drop is.
- **Graduated confidence scoring.** Not binary enter/don't-enter. Each opportunity gets a confidence score that feeds into Kelly sizing.
- **Pre-game entries are cautious.** Asymmetric information problem (injuries, matchday fitness, insider knowledge) makes pre-game speculation dangerous. Flag Kalshi/sportsbook misalignment but don't trade it initially. Collect data.

### Exit Logic
- **Default: ride to resolution.** The previous bot's stop-loss logic lost more money than no stop-loss would have. Prediction markets resolve — let them.
- **No premature complexity.** Kalshi allows selling before resolution, which is an advantage. But building sophisticated exit logic before understanding entry quality is putting the cart before the horse.
- **Future module:** Once paper trading data shows consistent patterns, explore exit optimization. But this is Phase 2+ work.

### Position Sizing (Kelly Criterion)
- Kelly criterion determines optimal bet size based on estimated edge and odds
- During paper trading: track what Kelly would have recommended and measure whether Kelly-sized portfolios outperform flat sizing
- Natural brake on uncertainty: low-confidence opportunities get small sizes, high-confidence get larger ones
- The cascade/falling-knife problem (favorite goes down 0-1, then 0-2) is partially addressed by Kelly — if confidence drops after Event 2, Kelly automatically reduces recommended size

### Self-Learning Loop
- **Not scheduled, data-driven.** Analysis runs after every resolved event. Insights surface when data crosses statistical significance thresholds, not on a calendar.
- **Advisory, not autonomous.** The system recommends changes. The human approves. Every change is logged with rationale and the data that supported it.
- **Change log as accountability.** Every parameter change records: what changed, why (with supporting statistics), and performance before/after. This is both an operational tool and a portfolio showcase.
- **Avoid overfitting to the past.** Markets change. Sports change. A pattern that held for 200 observations may not hold for the next 200. The system should track recency-weighted performance and flag when historical patterns may be degrading.

### Security (Public Repo)
- **No credentials in code.** Environment variables for all API keys, loaded from `.env` (gitignored).
- **No PII in data.** Paper trades contain market data, not personal information.
- **Sanitized dashboard.** If the dashboard is ever publicly accessible, it shows analysis and performance, not account details or API keys.
- **`.env.example`** with placeholder values committed. Real `.env` never committed.

## Tech Stack

### Python Backend
- **Python 3.12+** with **uv** for package management
- **FastAPI** — async web framework, automatic OpenAPI docs (portfolio-friendly)
- **asyncio + websockets** — concurrent market stream handling
- **Pydantic** — data validation and serialization (proven in kalshi-trade-analytics)
- **SQLAlchemy + Alembic** — database ORM and migrations
- **SQLite** for development, **PostgreSQL** for production/VPS
- **pandas / numpy / scipy** — statistical analysis
- **pytest** — testing

### TypeScript Dashboard
- **React 19** with **TypeScript**
- **Vite** — build tooling
- **TailwindCSS** — styling
- **Recharts or Visx** — charting/visualization
- **TanStack Query** — API data fetching and caching

### Infrastructure
- **Docker Compose** — local development and VPS deployment
- **GitHub Actions** — CI (linting, type checking, tests)

## Project Structure

```
kalshi-mean-reversion-bot/
├── backend/
│   ├── src/
│   │   ├── ingestion/        # Kalshi, ESPN, sportsbook data feeds
│   │   ├── strategy/         # Event detection, opportunity scoring
│   │   │   └── sports/       # Sport-specific classifiers
│   │   ├── paper_trader/     # Trade simulation, Kelly sizing
│   │   ├── analysis/         # Statistical engine, accumulators
│   │   ├── insights/         # Threshold detection, recommendations
│   │   ├── notifications/    # Email alerts
│   │   ├── api/              # FastAPI routes
│   │   ├── models/           # Pydantic schemas, DB models
│   │   └── core/             # Config, database, shared utilities
│   ├── tests/
│   ├── alembic/              # Database migrations
│   └── pyproject.toml
├── dashboard/
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── views/            # Page-level views
│   │   ├── api/              # API client
│   │   └── hooks/            # Custom React hooks
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Open Questions

1. **Which sportsbook API for the +1 odds source?** Need to evaluate DraftKings, FanDuel, The Odds API, etc. for free tier availability and data quality.
2. **Database choice for Phase 1** — SQLite is simpler for local dev and keeps the repo self-contained. PostgreSQL is better if we're deploying to a VPS soon. Leaning SQLite with a clean migration path.
3. **How aggressively to classify events at launch** — start with broad "score change" detection and let the data reveal which event types matter, or build the sport-specific classifiers (power play, penalty kick, etc.) from day one?
4. **Kalshi API authentication** — reuse the RSA-PSS auth pattern from the old bot, translated to Python. Need to verify the Python `cryptography` library supports the same signing scheme.

## Phases

### Phase 1: Data Collection & Paper Trading (Current)
- Kalshi market monitoring (WebSocket + REST)
- ESPN live game data integration
- Sportsbook odds ingestion (+1 source)
- Event detection (sport-agnostic core + initial sport classifiers)
- Paper trade simulation with Kelly criterion sizing
- Statistical analysis engine with running accumulators
- Insights generator with threshold-driven recommendations
- Dashboard with all Phase 1 views
- Email notifications for high-signal insights
- Approval workflow and change log

### Phase 2: Strategy Validation & Refinement
- ML-based event classification (temporary shock vs structural shift)
- Cascade analysis (multi-event sequences within a single game)
- Cross-sport pattern detection
- Backtesting framework against historical data
- Shadow model (experimental parameters running in parallel)

### Phase 3: Live Trading
- Kalshi order placement via REST API
- Position management and portfolio tracking
- Exit optimization (data-informed, not premature)
- Real capital risk controls (daily limits, max position size, kill switch)
- Live + paper trading running simultaneously

### Phase 4: Agent Integration
- Agent-facing API endpoints (query analysis, approve changes, trigger investigations)
- Webhook/notification hooks for external agent frameworks
- Conversational interface for strategy discussion

## Next Steps

Proceed to `/ce:plan` for implementation details — file-by-file breakdown, dependency setup, and build order.

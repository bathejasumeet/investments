# Investment Portfolio Planner & Tracker

A local, single-user desktop application for managing an investment portfolio. Track holdings with live market prices, get investment recommendations based on market trends, view interactive price charts, and analyze portfolio performance.

## Features

- **📊 Dashboard** — Portfolio summary with total value, gain/loss, and individual holding metrics
- **🎯 Goal Planner** — Define life goals (retirement, house, tuition), map holdings to each goal, and see probability of success via Monte Carlo simulation
- **�🇺 EU Investments** — European stocks, ETFs, and bond ETFs with 5-year performance deltas, interactive charts, benefit score ranking, and add-to-portfolio
- **🎯 Four-Fund Portfolio** — Bogleheads strategy page comparing ETFs by TER, AUM, and returns across four portfolio slots (EU stocks, developed world, emerging markets, bonds)
- **💼 Holdings Management** — Add, edit, and delete investment holdings with ticker validation
- **💡 Recommendations** — Explainable investment suggestions with transparent factor breakdown (momentum, valuation, volatility, volume, concentration impact)
- **📉 Price Charts** — Interactive Plotly charts with multiple time ranges (1D, 1W, 1M, 3M, 1Y)
- **📐 Analytics** — Asset allocation, sector exposure, and holding performance comparison

## Tech Stack

- **Language**: Python 3.11+
- **UI Framework**: Streamlit (browser-based local UI)
- **Database**: SQLite (local file-based, zero-config)
- **ORM**: SQLAlchemy 2.0
- **Market Data**: yfinance (Yahoo Finance API)
- **Charts**: Plotly
- **Testing**: pytest with TDD (Red-Green-Refactor)

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Internet connection (for market data; portfolio management works offline)

## Setup

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd investments
   ```

2. **Create a virtual environment**:

   ```bash
   python3 -m venv .venv
        # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment**:
   ```bash
   cp data/.env.example data/.env
   # Edit data/.env to set your API key (yfinance works without a key)
   ```

## Goal-Based Investing Planner

The **🎯 Goal Planner** page lets you define life goals and see your probability of success:

### How It Works

1. **Define Goals** — Create goals like "Retire at 60", "House in 7 years", or "College tuition fund" with a target amount, target date, and optional monthly contribution
2. **Map Holdings** — Link your portfolio holdings to each goal with an allocation percentage (a holding can be shared across multiple goals)
3. **Monte Carlo Simulation** — The system runs 100–5000 simulations per goal using geometric Brownian motion to project portfolio growth
4. **Probability of Success** — See the likelihood of reaching each goal, with median/worst-case/best-case projections and shortfall/surplus indicators

### Adjustable Assumptions

- **Expected Annual Return** — 0–15% (default: 7%)
- **Annual Volatility** — 5–40% (default: 15%)
- **Simulations** — 100, 500, 1000, or 5000 (more = more accurate but slower)

### Status Labels

| Probability | Label     | Indicator |
| ----------- | --------- | --------- |
| ≥ 80%       | On Track  | ✅        |
| 70–79%      | On Track  | ✅        |
| 30–69%      | At Risk   | ⚠️        |
| < 30%       | Off Track | 🚨        |

The dashboard also shows a goal progress preview with quick probability metrics.

## European Investment Options

The **🇪🇺 EU Investments** page provides a curated overview of European market investment opportunities:

### Supported Exchanges

| Exchange               | Ticker Suffix | Example     |
| ---------------------- | ------------- | ----------- |
| XETRA (Germany)        | `.DE`         | `SAP.DE`    |
| Euronext Amsterdam     | `.AS`         | `ASML.AS`   |
| Euronext Paris         | `.PA`         | `MC.PA`     |
| London Stock Exchange  | `.L`          | `AZN.L`     |
| Borsa Italiana (Milan) | `.MI`         | `ENI.MI`    |
| SIX Swiss Exchange     | `.SW`         | `NESN.SW`   |
| NASDAQ Stockholm       | `.ST`         | `ERIC-B.ST` |

### Asset Classes

- **Stocks** — ~25 major European stocks across Technology, Healthcare, Consumer, Finance, Energy, and Industrials sectors
- **ETFs** — ~12 UCITS ETFs (broad market, sector-specific, emerging markets)
- **Bond ETFs** — ~10 European bond ETFs (government, corporate, inflation-linked, EUR-hedged)

### Features

- **5-Year Performance Deltas** — 1Y, 3Y, and 5Y price change (absolute and percentage)
- **Interactive Charts** — Plotly line charts with 1Y/3Y/5Y time periods and hover tooltips
- **Benefit Score Ranking** — Composite score combining momentum (40%), 5Y return (40%), and volume (20%)
- **Search & Filter** — Filter by name, ticker, exchange, or sector
- **Add to Portfolio** — Add any European option directly to your portfolio
- **Multi-Currency** — Prices shown in original currency (EUR, GBP, CHF, SEK); base currency defaults to EUR

### Configuration

```bash
# data/.env
BASE_CURRENCY=EUR  # Default base currency for European market
```

## Explainable Recommendations

The **💡 Recommendations** page provides investment suggestions with a **transparent factor breakdown** — no black-box AI. Every recommendation's confidence score is a weighted sum of five explainable factors:

| Factor               | Weight | What it measures                   | How it's scored                           |
| -------------------- | ------ | ---------------------------------- | ----------------------------------------- |
| 🚀 **Momentum**      | 30%    | Recent price change (past month)   | +20% → 100%, -20% → 0% (linear)           |
| 💰 **Valuation**     | 20%    | Position within recent price range | Near the low → high score (better value)  |
| 📊 **Volatility**    | 15%    | Daily return std-dev               | Lower volatility → higher stability score |
| 📈 **Volume**        | 15%    | Average daily trading volume       | Higher volume → higher liquidity score    |
| 🎯 **Concentration** | 20%    | Portfolio overlap                  | New ticker → 100%; already held → 0%      |

### How the Confidence Score Works

```
Confidence = (Momentum × 0.30) + (Valuation × 0.20) + (Volatility × 0.15)
           + (Volume × 0.15) + (Concentration × 0.20)
```

Each factor score is normalized to **0.0–1.0** and accompanied by a human-readable explanation. The recommendation card displays:

- A visual score bar for each factor
- The weight and contribution of each factor
- A summary table showing how the composite score is assembled
- The top contributing factor highlighted in the rationale

This design ensures users can audit _why_ a ticker was recommended and make informed decisions based on the underlying metrics.

## Running the Application

```bash
streamlit run app/main.py
```

The app will open in your default browser at `http://localhost:8501`.
On startup, the application upgrades the local SQLite schema automatically. The
first upgrade also preserves existing portfolio data and removes duplicate cached
price points before enforcing one record per ticker and timestamp.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run only unit tests
pytest tests/unit/ -m unit

# Run only integration tests
pytest tests/integration/ -m integration
```

## Linting and Type Checking

```bash
# Lint with ruff
ruff check app/ tests/

# Format with ruff
ruff format app/ tests/

# Type check with mypy
mypy app/
```

## Project Structure

```
app/
├── main.py              # Streamlit entry point with navigation
├── database.py          # SQLAlchemy engine, session, Base
├── config.py            # App configuration from .env
├── data/                # Curated ticker universes (EU stocks, ETFs, bonds)
├── models/              # ORM models (Holding, PricePoint, Goal, GoalHoldingMapping, etc.)
├── repositories/        # Data access layer (Repository pattern)
├── services/            # Business logic (Portfolio, Goal, MarketData, InvestmentOption, etc.)
├── providers/           # Market data providers (Strategy pattern)
└── ui/                  # Streamlit views and components
    ├── dashboard.py
    ├── goal_planner.py    # Goal-based investing planner view
    ├── eu_investments.py  # European investment options view
    ├── holdings.py
    ├── recommendations.py
    ├── charts.py
    ├── analytics.py
    └── components/      # Reusable UI components (goal_card, holding_card, etc.)

tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
├── integration/         # Integration tests
├── contract/            # Contract tests
└── e2e/                 # End-to-end tests

data/                    # Local data (gitignored)
├── portfolio.db         # SQLite database
└── .env                 # Environment configuration
```

## Architecture

The application follows a clean layered architecture:

1. **Models** — SQLAlchemy ORM models defining database schema
2. **Repositories** — Data access layer implementing the Repository pattern
3. **Services** — Business logic layer with dependency injection
4. **Providers** — Market data abstraction using the Strategy pattern
5. **UI** — Streamlit views with reusable components

### Design Patterns Used

- **Repository Pattern** — Separates data access from business logic
- **Strategy Pattern** — Swappable market data providers
- **Dependency Injection** — Services receive dependencies at construction
- **Separation of Concerns** — Each layer has a single responsibility

## Constitution

This project follows a [constitution](.specify/memory/constitution.md) with 5 core principles:

1. **Strong Design Patterns** — Established patterns, DI, single responsibility
2. **Test-Driven Development** (NON-NEGOTIABLE) — Red-Green-Refactor cycle
3. **User Experience Consistency** — Design system, accessibility, four-state handling
4. **Code Simplicity & Readability** — YAGNI, complexity thresholds, clear naming
5. **CI/CD Readiness** — Trunk-based, never-broken main, automated checks

## License

Private project — All rights reserved.

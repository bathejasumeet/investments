# Investment Portfolio Planner & Tracker

A local, single-user desktop application for managing an investment portfolio. Track holdings with live market prices, get investment recommendations based on market trends, view interactive price charts, and analyze portfolio performance.

## Features

- **📊 Dashboard** — Portfolio summary with total value, gain/loss, and individual holding metrics
- **🇪🇺 EU Investments** — European stocks, ETFs, and bond ETFs with 5-year performance deltas, interactive charts, benefit score ranking, and add-to-portfolio
- **🎯 Four-Fund Portfolio** — Bogleheads strategy page comparing ETFs by TER, AUM, and returns across four portfolio slots (EU stocks, developed world, emerging markets, bonds)
- **💼 Holdings Management** — Add, edit, and delete investment holdings with ticker validation
- **💡 Recommendations** — AI-driven investment suggestions based on market trends and momentum
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
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
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

## Running the Application

```bash
streamlit run app/main.py
```

The app will open in your default browser at `http://localhost:8501`.

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
├── models/              # ORM models + dataclasses (Holding, PricePoint, InvestmentOption)
├── repositories/        # Data access layer (Repository pattern)
├── services/            # Business logic (Portfolio, MarketData, InvestmentOption, etc.)
├── providers/           # Market data providers (Strategy pattern)
└── ui/                  # Streamlit views and components
    ├── dashboard.py
    ├── eu_investments.py  # European investment options view
    ├── holdings.py
    ├── recommendations.py
    ├── charts.py
    ├── analytics.py
    └── components/      # Reusable UI components

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

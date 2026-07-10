# Tasks: Investment Portfolio Planner & Tracker

**Input**: Design documents from `/specs/001-investment-portfolio-tracker/`

**Prerequisites**: spec.md (required), constitution.md (TDD non-negotiable)

**Tests**: Included — Constitution Principle II mandates TDD (Red-Green-Refactor). Tests written FIRST, must FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `app/`, `tests/` at repository root
- Python with Streamlit (browser-based local UI), SQLite (local storage), SQLAlchemy ORM

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per implementation plan (app/, tests/, data/ directories)
- [x] T002 Initialize Python project with pyproject.toml including dependencies: streamlit, sqlalchemy, yfinance, pandas, plotly, pytest, pytest-cov, ruff, mypy
- [x] T003 [P] Configure linting and formatting tools (ruff.toml, mypy.ini) at repository root
- [x] T004 [P] Create .env.example template with MARKET_DATA_API_KEY placeholder in data/.env.example
- [x] T005 Create .gitignore excluding data/portfolio.db, data/.env, **pycache**/, .pytest_cache/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 [P] Create database engine and session factory in app/database.py (SQLAlchemy engine, SessionLocal, Base declarative)
- [x] T007 [P] Create app config loader in app/config.py (reads .env, exposes API key, DB path, base currency settings)
- [x] T008 Create Holding ORM model in app/models/holding.py (id, ticker, quantity, purchase_price, date_acquired, created_at, updated_at)
- [x] T009 [P] Create PricePoint ORM model in app/models/price_point.py (id, ticker, date, open, high, low, close, volume, fetched_at)
- [x] T010 [P] Create abstract market data provider interface in app/providers/base.py (MarketDataProvider ABC with get_current_price, get_price_history, validate_ticker, get_trend_data)
- [x] T011 [P] Create yfinance provider implementation in app/providers/yfinance_provider.py (implements MarketDataProvider using yfinance library)
- [x] T012 Create holding repository in app/repositories/holding_repository.py (CRUD: add, get_by_id, get_all, update, delete)
- [x] T013 [P] Create price repository in app/repositories/price_repository.py (save_price_points, get_history_by_ticker, get_latest_price)
- [x] T014 [P] Create shared test fixtures in tests/conftest.py (in-memory SQLite engine, session fixture, mock market data provider, sample holding factory)
- [x] T015 [P] Create reusable UI state indicators in app/ui/components/state_indicators.py (loading_spinner, empty_state, error_message, success_toast components)
- [x] T016 Create Streamlit app entry point with navigation in app/main.py (sidebar nav: Dashboard, Holdings, Recommendations, Charts, Analytics)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Portfolio Dashboard (Priority: P1) 🎯 MVP

**Goal**: User sees a dashboard summarizing their entire investment portfolio at a glance

**Independent Test**: Launch the app and verify the dashboard renders with all portfolio holdings, total value, and performance summary

### Tests for User Story 1 (TDD - Write FIRST, must FAIL) ⚠️

- [x] T017 [P] [US1] Unit test for portfolio value calculation in tests/unit/test_portfolio_service.py (test total value = sum of holding current values)
- [x] T018 [P] [US1] Unit test for gain/loss calculation in tests/unit/test_portfolio_service.py (test absolute and percentage gain/loss per holding)
- [x] T019 [P] [US1] Unit test for empty portfolio handling in tests/unit/test_portfolio_service.py (test zero holdings returns zero value, no crash)
- [x] T020 [P] [US1] Unit test for stale data detection in tests/unit/test_portfolio_service.py (test last_updated timestamp > 1 hour flags as stale)

### Implementation for User Story 1

- [x] T021 [US1] Create portfolio service in app/services/portfolio_service.py (calculate_total_value, calculate_gain_loss, get_portfolio_summary, check_data_freshness)
- [x] T022 [US1] Create market data service in app/services/market_data_service.py (fetch_current_prices for tickers, cache to price_repository, serve cached on failure)
- [x] T023 [US1] Create dashboard view in app/ui/dashboard.py (render total portfolio value, holdings table with price/quantity/value/gain-loss, stale data indicator)
- [x] T024 [US1] Create holding card component in app/ui/components/holding_card.py (displays single holding: ticker, quantity, current price, value, gain/loss with color coding)
- [x] T025 [US1] Integrate dashboard view into app/main.py navigation (dashboard as default landing page)
- [x] T026 [US1] Add empty state handling to dashboard (when no holdings exist, show guidance to add first holding)

**Checkpoint**: User Story 1 fully functional — dashboard renders portfolio with live/cached prices

---

## Phase 4: User Story 2 - Add & Manage Portfolio Holdings (Priority: P1)

**Goal**: User can add, edit, and remove investment holdings so the portfolio accurately reflects what they own

**Independent Test**: Add a holding (ticker + quantity + purchase price), verify it appears in dashboard. Edit quantity, verify updates. Remove holding, verify it's gone.

### Tests for User Story 2 (TDD - Write FIRST, must FAIL) ⚠️

- [x] T027 [P] [US2] Integration test for holding repository add operation in tests/integration/test_holding_repository.py (test add holding persists to DB)
- [x] T028 [P] [US2] Integration test for holding repository update/delete in tests/integration/test_holding_repository.py (test edit quantity, delete holding)
- [x] T029 [P] [US2] Unit test for ticker validation in tests/unit/test_market_data_service.py (test valid ticker accepted, invalid ticker rejected)
- [x] T030 [P] [US2] Unit test for duplicate ticker handling in tests/unit/test_portfolio_service.py (test adding same ticker twice updates quantity vs. creates new)

### Implementation for User Story 2

- [x] T031 [US2] Create holdings management view in app/ui/holdings.py (add form: ticker, quantity, purchase price; edit form; delete button per holding)
- [x] T032 [US2] Implement ticker validation in app/services/market_data_service.py (validate_ticker calls provider.validate_ticker before saving)
- [x] T033 [US2] Add form validation and error display in app/ui/holdings.py (invalid ticker error, negative quantity error, missing fields error)
- [x] T034 [US2] Implement edit holding flow in app/ui/holdings.py (load existing values into form, save updates, recalculate portfolio)
- [x] T035 [US2] Implement delete holding with confirmation in app/ui/holdings.py (confirm dialog, delete via repository, update dashboard)
- [x] T036 [US2] Integrate holdings view into app/main.py navigation

**Checkpoint**: User Stories 1 AND 2 both work — user can manage holdings and see them on dashboard

---

## Phase 5: User Story 3 - View Investment Recommendations (Priority: P2)

**Goal**: Application suggests investment options based on current market trends

**Independent Test**: Navigate to recommendations view and verify a ranked list of suggested investments with key metrics is displayed

### Tests for User Story 3 (TDD - Write FIRST, must FAIL) ⚠️

- [x] T037 [P] [US3] Unit test for recommendation ranking in tests/unit/test_recommendation_service.py (test recommendations sorted by confidence score descending)
- [x] T038 [P] [US3] Unit test for trend direction calculation in tests/unit/test_recommendation_service.py (test up/down/flat trend from price history)
- [x] T039 [P] [US3] Unit test for portfolio overlap detection in tests/unit/test_recommendation_service.py (test flagging recommendations already in portfolio)
- [x] T040 [P] [US3] Unit test for stale recommendation data in tests/unit/test_recommendation_service.py (test freshness warning when data > 1 hour old)

### Implementation for User Story 3

- [x] T041 [US3] Create recommendation service in app/services/recommendation_service.py (fetch top gainers, calculate momentum, rank by confidence, detect portfolio overlap)
- [x] T042 [US3] Create recommendations view in app/ui/recommendations.py (ranked list with ticker, price, trend, sector, confidence score, overlap indicator)
- [x] T043 [US3] Create recommendation card component in app/ui/components/recommendation_card.py (displays single recommendation with metrics and rationale)
- [x] T044 [US3] Add data freshness indicator to recommendations view (warning banner when last update > 1 hour)
- [x] T045 [US3] Add manual refresh button to recommendations view (triggers recommendation_service to fetch fresh data)
- [x] T046 [US3] Integrate recommendations view into app/main.py navigation

**Checkpoint**: User Story 3 functional — user can view and refresh investment recommendations

---

## Phase 6: User Story 4 - Track Price Trends & Market Data (Priority: P2)

**Goal**: User can see price history and trend data for holdings and recommended investments

**Independent Test**: Select any holding or recommended investment, view price chart over multiple time periods (1D, 1W, 1M, 3M, 1Y), verify data points render correctly

### Tests for User Story 4 (TDD - Write FIRST, must FAIL) ⚠️

- [x] T047 [P] [US4] Unit test for chart data preparation in tests/unit/test_chart_service.py (test price history converted to Plotly-compatible format)
- [x] T048 [P] [US4] Unit test for time range filtering in tests/unit/test_chart_service.py (test 1D/1W/1M/3M/1Y filters return correct date ranges)
- [x] T049 [P] [US4] Unit test for insufficient data handling in tests/unit/test_chart_service.py (test partial data renders without extrapolation)
- [x] T050 [P] [US4] Integration test for price history retrieval in tests/integration/test_price_repository.py (test get_history_by_ticker returns chronological price points)

### Implementation for User Story 4

- [x] T051 [US4] Create chart service in app/services/chart_service.py (prepare_chart_data: fetch price history, filter by time range, format for Plotly)
- [x] T052 [US4] Create charts view in app/ui/charts.py (ticker selector, time range buttons 1D/1W/1M/3M/1Y, interactive Plotly candlestick/line chart)
- [x] T053 [US4] Add hover tooltip to chart in app/ui/charts.py (display exact price, date, volume on data point hover)
- [x] T054 [US4] Add insufficient data handling to charts view (show available data only, no extrapolation, message if no data for selected range)
- [x] T055 [US4] Integrate charts view into app/main.py navigation

**Checkpoint**: User Story 4 functional — user can view interactive price charts for any holding or recommendation

---

## Phase 7: User Story 5 - Portfolio Performance Analytics (Priority: P3)

**Goal**: User sees analytics on portfolio performance — allocation breakdown, sector exposure, and return comparisons

**Independent Test**: View analytics section and verify allocation pie chart, sector breakdown, and performance metrics are computed from portfolio data

### Tests for User Story 5 (TDD - Write FIRST, must FAIL) ⚠️

- [x] T056 [P] [US5] Unit test for allocation calculation in tests/unit/test_portfolio_service.py (test asset allocation percentages sum to 100%)
- [x] T057 [P] [US5] Unit test for sector exposure in tests/unit/test_portfolio_service.py (test sector breakdown groups holdings by sector)
- [x] T058 [P] [US5] Unit test for return comparison in tests/unit/test_portfolio_service.py (test individual holding returns ranked and compared)
- [x] T059 [P] [US5] Unit test for single holding diversification suggestion in tests/unit/test_portfolio_service.py (test 100% allocation triggers diversify suggestion)

### Implementation for User Story 5

- [x] T060 [US5] Extend portfolio service with analytics methods in app/services/portfolio_service.py (calculate_allocation, calculate_sector_exposure, compare_holding_performance)
- [x] T061 [US5] Create analytics view in app/ui/analytics.py (allocation pie chart, sector breakdown bar chart, holding performance comparison table)
- [x] T062 [US5] Add diversification suggestion to analytics view in app/ui/analytics.py (show suggestion when single holding = 100% allocation)
- [x] T063 [US5] Add refresh analytics button in app/ui/analytics.py (recalculate all metrics with latest prices)
- [x] T064 [US5] Integrate analytics view into app/main.py navigation

**Checkpoint**: All user stories independently functional — full application operational

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T065 [P] Create CSV export service in app/services/export_service.py (export holdings + performance history to CSV)
- [x] T066 [P] Add CSV export button to dashboard in app/ui/dashboard.py (triggers export_service, downloads file)
- [x] T067 [P] Create corporate action alert logic in app/services/market_data_service.py (detect stock splits, symbol changes, alert user)
- [x] T068 [P] Add corporate action alerts to dashboard in app/ui/dashboard.py (display alert banner when corporate action detected)
- [x] T069 [P] Add base currency configuration to app/config.py and app/ui/holdings.py (user can set base currency, all values normalized)
- [x] T070 [P] Create README.md at repository root with setup instructions, API key configuration, and run commands
- [x] T071 Code cleanup and refactoring across all modules (verify function < 30 lines, files < 400 lines, cyclomatic complexity < 10)
- [x] T072 [P] Add unit tests for export service in tests/unit/test_export_service.py (test CSV format, test complete export, test empty portfolio export)
- [x] T073 [P] Add E2E test for add-holding-to-dashboard journey in tests/e2e/test_user_journeys.py (add holding → verify dashboard updates)
- [x] T074 [P] Add E2E test for refresh-recommendations journey in tests/e2e/test_user_journeys.py (open recommendations → refresh → verify new data)
- [x] T075 Run quickstart.md validation scenarios (if quickstart.md exists) or manual validation of all 5 user stories
- [x] T076 Security hardening: verify no secrets in code, .env in .gitignore, input validation on all forms

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (Dashboard) and US2 (Holdings) are both P1 and can proceed in parallel
  - US3 (Recommendations) and US4 (Charts) are P2 and can proceed in parallel after P1 stories
  - US5 (Analytics) is P3 and depends on US1 (needs portfolio service) but can proceed after US1
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - Dashboard)**: Can start after Foundational — No dependencies on other stories
- **User Story 2 (P1 - Holdings)**: Can start after Foundational — No dependencies on other stories (but dashboard benefits from having holdings to display)
- **User Story 3 (P2 - Recommendations)**: Can start after Foundational — Independent, but benefits from US2 (portfolio overlap detection)
- **User Story 4 (P2 - Charts)**: Can start after Foundational — Independent, works with any ticker (holding or recommendation)
- **User Story 5 (P3 - Analytics)**: Depends on US1 (uses portfolio_service) — Can start after US1 completes

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD - Constitution Principle II)
- Models before services
- Services before UI views
- Core implementation before integration into main.py navigation
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- US1 and US2 can be developed in parallel (both P1, minimal cross-dependency)
- US3 and US4 can be developed in parallel (both P2, independent)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD - write first, verify they fail):
Task: "Unit test for portfolio value calculation in tests/unit/test_portfolio_service.py"
Task: "Unit test for gain/loss calculation in tests/unit/test_portfolio_service.py"
Task: "Unit test for empty portfolio handling in tests/unit/test_portfolio_service.py"
Task: "Unit test for stale data detection in tests/unit/test_portfolio_service.py"

# Then implement sequentially (services before UI):
Task: "Create portfolio service in app/services/portfolio_service.py"
Task: "Create market data service in app/services/market_data_service.py"
Task: "Create dashboard view in app/ui/dashboard.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Dashboard)
4. Complete Phase 4: User Story 2 (Holdings Management)
5. **STOP and VALIDATE**: Test that user can add holdings and see them on dashboard
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + 2 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 3 + 4 → Test independently → Deploy/Demo
4. Add User Story 5 → Test independently → Deploy/Demo
5. Complete Polish phase → Full application

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Dashboard)
   - Developer B: User Story 2 (Holdings)
3. After P1 stories:
   - Developer A: User Story 3 (Recommendations)
   - Developer B: User Story 4 (Charts)
4. After P2 stories:
   - Developer A: User Story 5 (Analytics)
   - Developer B: Polish phase tasks

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD is NON-NEGOTIABLE** (Constitution Principle II) — tests MUST be written first and fail before implementation
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

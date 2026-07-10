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

- [ ] T001 Create project structure per implementation plan (app/, tests/, data/ directories)
- [ ] T002 Initialize Python project with pyproject.toml including dependencies: streamlit, sqlalchemy, yfinance, pandas, plotly, pytest, pytest-cov, ruff, mypy
- [ ] T003 [P] Configure linting and formatting tools (ruff.toml, mypy.ini) at repository root
- [ ] T004 [P] Create .env.example template with MARKET_DATA_API_KEY placeholder in data/.env.example
- [ ] T005 Create .gitignore excluding data/portfolio.db, data/.env, **pycache**/, .pytest_cache/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 [P] Create database engine and session factory in app/database.py (SQLAlchemy engine, SessionLocal, Base declarative)
- [ ] T007 [P] Create app config loader in app/config.py (reads .env, exposes API key, DB path, base currency settings)
- [ ] T008 Create Holding ORM model in app/models/holding.py (id, ticker, quantity, purchase_price, date_acquired, created_at, updated_at)
- [ ] T009 [P] Create PricePoint ORM model in app/models/price_point.py (id, ticker, date, open, high, low, close, volume, fetched_at)
- [ ] T010 [P] Create abstract market data provider interface in app/providers/base.py (MarketDataProvider ABC with get_current_price, get_price_history, validate_ticker, get_trend_data)
- [ ] T011 [P] Create yfinance provider implementation in app/providers/yfinance_provider.py (implements MarketDataProvider using yfinance library)
- [ ] T012 Create holding repository in app/repositories/holding_repository.py (CRUD: add, get_by_id, get_all, update, delete)
- [ ] T013 [P] Create price repository in app/repositories/price_repository.py (save_price_points, get_history_by_ticker, get_latest_price)
- [ ] T014 [P] Create shared test fixtures in tests/conftest.py (in-memory SQLite engine, session fixture, mock market data provider, sample holding factory)
- [ ] T015 [P] Create reusable UI state indicators in app/ui/components/state_indicators.py (loading_spinner, empty_state, error_message, success_toast components)
- [ ] T016 Create Streamlit app entry point with navigation in app/main.py (sidebar nav: Dashboard, Holdings, Recommendations, Charts, Analytics)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Portfolio Dashboard (Priority: P1) 🎯 MVP

**Goal**: User sees a dashboard summarizing their entire investment portfolio at a glance

**Independent Test**: Launch the app and verify the dashboard renders with all portfolio holdings, total value, and performance summary

### Tests for User Story 1 (TDD - Write FIRST, must FAIL) ⚠️

- [ ] T017 [P] [US1] Unit test for portfolio value calculation in tests/unit/test_portfolio_service.py (test total value = sum of holding current values)
- [ ] T018 [P] [US1] Unit test for gain/loss calculation in tests/unit/test_portfolio_service.py (test absolute and percentage gain/loss per holding)
- [ ] T019 [P] [US1] Unit test for empty portfolio handling in tests/unit/test_portfolio_service.py (test zero holdings returns zero value, no crash)
- [ ] T020 [P] [US1] Unit test for stale data detection in tests/unit/test_portfolio_service.py (test last_updated timestamp > 1 hour flags as stale)

### Implementation for User Story 1

- [ ] T021 [US1] Create portfolio service in app/services/portfolio_service.py (calculate_total_value, calculate_gain_loss, get_portfolio_summary, check_data_freshness)
- [ ] T022 [US1] Create market data service in app/services/market_data_service.py (fetch_current_prices for tickers, cache to price_repository, serve cached on failure)
- [ ] T023 [US1] Create dashboard view in app/ui/dashboard.py (render total portfolio value, holdings table with price/quantity/value/gain-loss, stale data indicator)
- [ ] T024 [US1] Create holding card component in app/ui/components/holding_card.py (displays single holding: ticker, quantity, current price, value, gain/loss with color coding)
- [ ] T025 [US1] Integrate dashboard view into app/main.py navigation (dashboard as default landing page)
- [ ] T026 [US1] Add empty state handling to dashboard (when no holdings exist, show guidance to add first holding)

**Checkpoint**: User Story 1 fully functional — dashboard renders portfolio with live/cached prices

---

## Phase 4: User Story 2 - Add & Manage Portfolio Holdings (Priority: P1)

**Goal**: User can add, edit, and remove investment holdings so the portfolio accurately reflects what they own

**Independent Test**: Add a holding (ticker + quantity + purchase price), verify it appears in dashboard. Edit quantity, verify updates. Remove holding, verify it's gone.

### Tests for User Story 2 (TDD - Write FIRST, must FAIL) ⚠️

- [ ] T027 [P] [US2] Integration test for holding repository add operation in tests/integration/test_holding_repository.py (test add holding persists to DB)
- [ ] T028 [P] [US2] Integration test for holding repository update/delete in tests/integration/test_holding_repository.py (test edit quantity, delete holding)
- [ ] T029 [P] [US2] Unit test for ticker validation in tests/unit/test_market_data_service.py (test valid ticker accepted, invalid ticker rejected)
- [ ] T030 [P] [US2] Unit test for duplicate ticker handling in tests/unit/test_portfolio_service.py (test adding same ticker twice updates quantity vs. creates new)

### Implementation for User Story 2

- [ ] T031 [US2] Create holdings management view in app/ui/holdings.py (add form: ticker, quantity, purchase price; edit form; delete button per holding)
- [ ] T032 [US2] Implement ticker validation in app/services/market_data_service.py (validate_ticker calls provider.validate_ticker before saving)
- [ ] T033 [US2] Add form validation and error display in app/ui/holdings.py (invalid ticker error, negative quantity error, missing fields error)
- [ ] T034 [US2] Implement edit holding flow in app/ui/holdings.py (load existing values into form, save updates, recalculate portfolio)
- [ ] T035 [US2] Implement delete holding with confirmation in app/ui/holdings.py (confirm dialog, delete via repository, update dashboard)
- [ ] T036 [US2] Integrate holdings view into app/main.py navigation

**Checkpoint**: User Stories 1 AND 2 both work — user can manage holdings and see them on dashboard

---

## Phase 5: User Story 3 - View Investment Recommendations (Priority: P2)

**Goal**: Application suggests investment options based on current market trends

**Independent Test**: Navigate to recommendations view and verify a ranked list of suggested investments with key metrics is displayed

### Tests for User Story 3 (TDD - Write FIRST, must FAIL) ⚠️

- [ ] T037 [P] [US3] Unit test for recommendation ranking in tests/unit/test_recommendation_service.py (test recommendations sorted by confidence score descending)
- [ ] T038 [P] [US3] Unit test for trend direction calculation in tests/unit/test_recommendation_service.py (test up/down/flat trend from price history)
- [ ] T039 [P] [US3] Unit test for portfolio overlap detection in tests/unit/test_recommendation_service.py (test flagging recommendations already in portfolio)
- [ ] T040 [P] [US3] Unit test for stale recommendation data in tests/unit/test_recommendation_service.py (test freshness warning when data > 1 hour old)

### Implementation for User Story 3

- [ ] T041 [US3] Create recommendation service in app/services/recommendation_service.py (fetch top gainers, calculate momentum, rank by confidence, detect portfolio overlap)
- [ ] T042 [US3] Create recommendations view in app/ui/recommendations.py (ranked list with ticker, price, trend, sector, confidence score, overlap indicator)
- [ ] T043 [US3] Create recommendation card component in app/ui/components/recommendation_card.py (displays single recommendation with metrics and rationale)
- [ ] T044 [US3] Add data freshness indicator to recommendations view (warning banner when last update > 1 hour)
- [ ] T045 [US3] Add manual refresh button to recommendations view (triggers recommendation_service to fetch fresh data)
- [ ] T046 [US3] Integrate recommendations view into app/main.py navigation

**Checkpoint**: User Story 3 functional — user can view and refresh investment recommendations

---

## Phase 6: User Story 4 - Track Price Trends & Market Data (Priority: P2)

**Goal**: User can see price history and trend data for holdings and recommended investments

**Independent Test**: Select any holding or recommended investment, view price chart over multiple time periods (1D, 1W, 1M, 3M, 1Y), verify data points render correctly

### Tests for User Story 4 (TDD - Write FIRST, must FAIL) ⚠️

- [ ] T047 [P] [US4] Unit test for chart data preparation in tests/unit/test_chart_service.py (test price history converted to Plotly-compatible format)
- [ ] T048 [P] [US4] Unit test for time range filtering in tests/unit/test_chart_service.py (test 1D/1W/1M/3M/1Y filters return correct date ranges)
- [ ] T049 [P] [US4] Unit test for insufficient data handling in tests/unit/test_chart_service.py (test partial data renders without extrapolation)
- [ ] T050 [P] [US4] Integration test for price history retrieval in tests/integration/test_price_repository.py (test get_history_by_ticker returns chronological price points)

### Implementation for User Story 4

- [ ] T051 [US4] Create chart service in app/services/chart_service.py (prepare_chart_data: fetch price history, filter by time range, format for Plotly)
- [ ] T052 [US4] Create charts view in app/ui/charts.py (ticker selector, time range buttons 1D/1W/1M/3M/1Y, interactive Plotly candlestick/line chart)
- [ ] T053 [US4] Add hover tooltip to chart in app/ui/charts.py (display exact price, date, volume on data point hover)
- [ ] T054 [US4] Add insufficient data handling to charts view (show available data only, no extrapolation, message if no data for selected range)
- [ ] T055 [US4] Integrate charts view into app/main.py navigation

**Checkpoint**: User Story 4 functional — user can view interactive price charts for any holding or recommendation

---

## Phase 7: User Story 5 - Portfolio Performance Analytics (Priority: P3)

**Goal**: User sees analytics on portfolio performance — allocation breakdown, sector exposure, and return comparisons

**Independent Test**: View analytics section and verify allocation pie chart, sector breakdown, and performance metrics are computed from portfolio data

### Tests for User Story 5 (TDD - Write FIRST, must FAIL) ⚠️

- [ ] T056 [P] [US5] Unit test for allocation calculation in tests/unit/test_portfolio_service.py (test asset allocation percentages sum to 100%)
- [ ] T057 [P] [US5] Unit test for sector exposure in tests/unit/test_portfolio_service.py (test sector breakdown groups holdings by sector)
- [ ] T058 [P] [US5] Unit test for return comparison in tests/unit/test_portfolio_service.py (test individual holding returns ranked and compared)
- [ ] T059 [P] [US5] Unit test for single holding diversification suggestion in tests/unit/test_portfolio_service.py (test 100% allocation triggers diversify suggestion)

### Implementation for User Story 5

- [ ] T060 [US5] Extend portfolio service with analytics methods in app/services/portfolio_service.py (calculate_allocation, calculate_sector_exposure, compare_holding_performance)
- [ ] T061 [US5] Create analytics view in app/ui/analytics.py (allocation pie chart, sector breakdown bar chart, holding performance comparison table)
- [ ] T062 [US5] Add diversification suggestion to analytics view in app/ui/analytics.py (show suggestion when single holding = 100% allocation)
- [ ] T063 [US5] Add refresh analytics button in app/ui/analytics.py (recalculate all metrics with latest prices)
- [ ] T064 [US5] Integrate analytics view into app/main.py navigation

**Checkpoint**: All user stories independently functional — full application operational

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T065 [P] Create CSV export service in app/services/export_service.py (export holdings + performance history to CSV)
- [ ] T066 [P] Add CSV export button to dashboard in app/ui/dashboard.py (triggers export_service, downloads file)
- [ ] T067 [P] Create corporate action alert logic in app/services/market_data_service.py (detect stock splits, symbol changes, alert user)
- [ ] T068 [P] Add corporate action alerts to dashboard in app/ui/dashboard.py (display alert banner when corporate action detected)
- [ ] T069 [P] Add base currency configuration to app/config.py and app/ui/holdings.py (user can set base currency, all values normalized)
- [ ] T070 [P] Create README.md at repository root with setup instructions, API key configuration, and run commands
- [ ] T071 Code cleanup and refactoring across all modules (verify function < 30 lines, files < 400 lines, cyclomatic complexity < 10)
- [ ] T072 [P] Add unit tests for export service in tests/unit/test_export_service.py (test CSV format, test complete export, test empty portfolio export)
- [ ] T073 [P] Add E2E test for add-holding-to-dashboard journey in tests/e2e/test_user_journeys.py (add holding → verify dashboard updates)
- [ ] T074 [P] Add E2E test for refresh-recommendations journey in tests/e2e/test_user_journeys.py (open recommendations → refresh → verify new data)
- [ ] T075 Run quickstart.md validation scenarios (if quickstart.md exists) or manual validation of all 5 user stories
- [ ] T076 Security hardening: verify no secrets in code, .env in .gitignore, input validation on all forms

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

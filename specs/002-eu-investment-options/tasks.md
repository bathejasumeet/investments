# Tasks: European Market Investment Options

**Input**: Design documents from `/specs/002-eu-investment-options/`

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
- Extends existing architecture — provider pattern, repository pattern, service layer

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare project configuration and curated data for European market support

- [x] T001 Add BASE_CURRENCY configuration defaulting to EUR in app/config.py
- [x] T002 [P] Create curated European ticker universe file in app/data/eu_ticker_universes.py (lists of EU_STOCKS with ~25 tickers across XETRA/Euronext/LSE/Milan/Zurich/Stockholm, EU_ETF with ~12 UCITS ETFs, EU_BOND_ETF with ~10 bond ETFs — each with ticker, name, exchange, sector, asset_class metadata)
- [x] T003 [P] Update .env.example in data/.env.example with BASE_CURRENCY=EUR and FRED_API_KEY placeholder for future bond context

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and provider extensions that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Create InvestmentOption dataclass in app/models/investment_option.py (ticker, name, exchange, asset_class, sector, current_price, currency, benefit_score fields)
- [x] T005 [P] Create PerformanceDelta dataclass in app/models/investment_option.py (period: 1Y/3Y/5Y, start_date, end_date, start_price, end_price, absolute_change, percentage_change)
- [x] T006 [P] Create BondMarketContext dataclass in app/models/investment_option.py (treasury_2y, treasury_5y, treasury_10y, treasury_30y, yield_curve_signal, ecb_deposit_rate, timestamp)
- [x] T007 [P] Create ExchangeRate dataclass in app/models/investment_option.py (source_currency, target_currency, rate, timestamp)
- [x] T008 [P] Create BenefitScore dataclass in app/models/investment_option.py (momentum_weight, return_weight, volume_weight, composite_score, component_breakdown)
- [x] T009 Extend MarketDataProvider abstract class in app/providers/base.py (add get_price_history_5y method returning PriceHistory for 5-year period, add get_exchange_rate method returning ExchangeRate)
- [x] T010 Extend YFinanceProvider in app/providers/yfinance_provider.py (add "5Y" period mapping, implement get_price_history_5y using yfinance period="5y", implement get_exchange_rate for EUR/USD/GBP/CHF/SEK cross rates)
- [x] T011 Create investment option service in app/services/investment_option_service.py (load_ticker_universe, fetch_all_options with current prices, calculate_benefit_scores, get_options_by_category)

**Checkpoint**: Foundation ready — data models, provider extensions, and service layer complete

---

## Phase 3: User Story 1 — View European Investment Options Overview (Priority: P1) 🎯 MVP

**Goal**: User sees a curated overview of European stocks, ETFs, and bond ETFs with current prices on app startup

**Independent Test**: Launch the app and verify the European Investment Options section loads with three categorized tabs showing stocks, ETFs, and bond ETFs — each with current price, name, exchange, and asset class label

### Tests for User Story 1 (TDD — Write FIRST, must FAIL) ⚠️

- [x] T012 [P] [US1] Unit test for loading ticker universe in tests/unit/test_investment_option_service.py (test load_ticker_universe returns correct counts per category, test each option has required fields populated)
- [x] T013 [P] [US1] Unit test for fetching current prices for EU tickers in tests/unit/test_investment_option_service.py (test fetch_all_options returns PriceQuote for each ticker, test handles provider failures gracefully)
- [x] T014 [P] [US1] Unit test for categorization in tests/unit/test_investment_option_service.py (test get_options_by_category returns separate lists for stock/ETF/bond)

### Implementation for User Story 1

- [x] T015 [P] [US1] Create European investment options UI component in app/ui/components/investment_option_card.py (render single option: name, ticker, exchange badge, current price, currency, asset class pill with color coding)
- [x] T016 [US1] Create European investment options view in app/ui/eu_investments.py (section header, three tabbed categories: Stocks/ETFs/Bonds, each showing list of InvestmentOption cards with current price, stale data indicator, loading spinner)
- [x] T017 [US1] Add European Investment Options section to dashboard in app/ui/dashboard.py (render EU investment options below portfolio holdings, visible on app startup)
- [x] T018 [US1] Add "🇪🇺 EU Investments" navigation entry in app/main.py sidebar radio options
- [x] T019 [US1] Add offline/cached data handling to investment option service in app/services/investment_option_service.py (cache fetched options, serve cached data when provider fails, track staleness timestamp)

**Checkpoint**: User Story 1 fully functional — European investment options display with live/cached prices on startup

---

## Phase 4: User Story 2 — View 5-Year Performance Delta & Charts (Priority: P1)

**Goal**: User sees 1Y/3Y/5Y performance deltas with interactive charts for each European investment option

**Independent Test**: Select any European investment option and verify 1Y/3Y/5Y deltas display with percentage and absolute change. Verify interactive charts render for each time period with hover tooltips.

### Tests for User Story 2 (TDD — Write FIRST, must FAIL) ⚠️

- [x] T020 [P] [US2] Unit test for 5-year price history retrieval in tests/unit/test_investment_option_service.py (test fetch_price_history returns PriceHistory with data points spanning 5 years, test handles instruments with < 5 years history)
- [x] T021 [P] [US2] Unit test for performance delta calculation in tests/unit/test_investment_option_service.py (test calculate_delta for 1Y/3Y/5Y returns correct absolute and percentage change, test edge case: only 6 months of data returns delta for available range)
- [x] T022 [P] [US2] Unit test for chart data preparation in tests/unit/test_investment_option_service.py (test prepare_chart_data formats price history into Plotly-compatible arrays for each time period)

### Implementation for User Story 2

- [x] T023 [US2] Add performance delta calculation to investment option service in app/services/investment_option_service.py (calculate_performance_deltas: fetch 5Y history, compute 1Y/3Y/5Y deltas from available data, handle partial data gracefully)
- [x] T024 [US2] Add chart data preparation to investment option service in app/services/investment_option_service.py (prepare_eu_chart_data: filter 5Y history to selected period, format dates/prices for Plotly line chart)
- [x] T025 [P] [US2] Create performance delta display component in app/ui/components/investment_option_card.py (extend card to show 1Y/3Y/5Y deltas with green/red color coding, show "Data since YYYY" note when < 5 years available)
- [x] T026 [US2] Add interactive chart to European investment options view in app/ui/eu_investments.py (expandable chart per option, time period selector 1Y/3Y/5Y, Plotly line chart with hover tooltip showing exact price, date, and % change from start)
- [x] T027 [US2] Add chart loading states and error handling in app/ui/eu_investments.py (spinner while loading chart data, error message if data unavailable, graceful fallback to partial data)

**Checkpoint**: User Stories 1 AND 2 functional — options display with full 5-year performance data and interactive charts

---

## Phase 5: User Story 3 — View Sorted Rankings by Benefit (Priority: P1)

**Goal**: Options are sorted from most to least beneficial using a composite benefit score, with alternative sort options

**Independent Test**: Verify options within each category are sorted by benefit score descending by default. Change sort to "Highest 5Y Return" and verify re-sort. Verify score components are visible.

### Tests for User Story 3 (TDD — Write FIRST, must FAIL) ⚠️

- [x] T028 [P] [US3] Unit test for benefit score calculation in tests/unit/test_investment_option_service.py (test composite score = momentum*0.4 + return*0.4 + volume\*0.2, test score range 0-1, test deterministic ordering for identical inputs)
- [x] T029 [P] [US3] Unit test for alternative sort criteria in tests/unit/test_investment_option_service.py (test sort by "Highest 5Y Return" orders by 5Y delta descending, test sort by "Most Traded" orders by volume descending)

### Implementation for User Story 3

- [x] T030 [US3] Implement benefit score calculation in app/services/investment_option_service.py (calculate_benefit_score: momentum from 1Y delta, return from 5Y delta, volume from recent trading volume, weighted composite normalized to 0-1)
- [x] T031 [US3] Add sorting logic to investment option service in app/services/investment_option_service.py (sort_options: support benefit_score/return_5y/volume sort criteria, default to benefit_score descending)
- [x] T032 [P] [US3] Add benefit score display to investment option card in app/ui/components/investment_option_card.py (show composite score with breakdown tooltip: momentum X%, return X%, volume X%)
- [x] T033 [US3] Add sort selector to European investment options view in app/ui/eu_investments.py (dropdown with sort criteria, re-sorts list on selection, maintains category tabs)

**Checkpoint**: User Story 3 functional — benefit score ranking with alternative sort options working

---

## Phase 6: User Story 4 — Add Investment Option to Portfolio (Priority: P2)

**Goal**: User can add any European investment option directly to their portfolio from the overview

**Independent Test**: Click "Add to Portfolio" on a European option, verify pre-filled form appears, submit with valid data, verify holding appears in Holdings page.

### Tests for User Story 4 (TDD — Write FIRST, must FAIL) ⚠️

- [x] T034 [P] [US4] Unit test for add-to-portfolio flow in tests/unit/test_investment_option_service.py (test create_holding_from_option pre-fills ticker and current price, test validates quantity > 0 and purchase_price > 0)
- [x] T035 [P] [US4] Integration test for EU holding persistence in tests/integration/test_holding_repository.py (test adding EU ticker holding persists to DB, test ticker with exchange suffix like SAP.DE is stored correctly)

### Implementation for User Story 4

- [x] T036 [US4] Add "Add to Portfolio" integration in app/ui/eu_investments.py (button on each option card, opens form pre-filled with ticker and current price, quantity and purchase price inputs, validation, submit via HoldingRepository)
- [x] T037 [US4] Add "In Portfolio" badge to investment option card in app/ui/components/investment_option_card.py (check if ticker exists in user's holdings, show "✅ In Portfolio" badge, disable add button)
- [x] T038 [US4] Update portfolio overlap detection in app/ui/eu_investments.py (load user's existing tickers on view load, mark matching options as "In Portfolio")

**Checkpoint**: User Story 4 functional — user can add European options to portfolio from the overview

---

## Phase 7: User Story 5 — Filter and Search Investment Options (Priority: P2)

**Goal**: User can search and filter European investment options by name, ticker, exchange, or sector

**Independent Test**: Type "SAP" in search and verify filtered results. Select "XETRA" exchange filter and verify only XETRA options shown. Clear filters and verify full list returns.

### Tests for User Story 5 (TDD — Write FIRST, must FAIL) ⚠️

- [x] T039 [P] [US5] Unit test for search filtering in tests/unit/test_investment_option_service.py (test filter by ticker substring, test filter by name substring, test filter by sector, test case-insensitive matching)
- [x] T040 [P] [US5] Unit test for exchange filtering in tests/unit/test_investment_option_service.py (test filter by single exchange returns only that exchange's options, test multiple exchange filter)

### Implementation for User Story 5

- [x] T041 [US5] Add search/filter logic to investment option service in app/services/investment_option_service.py (filter_options: search by name/ticker/sector substring, filter by exchange list, filter by asset_class, compose multiple filters)
- [x] T042 [US5] Add search bar and filter controls to European investment options view in app/ui/eu_investments.py (text search input, exchange multi-select dropdown, sector dropdown, clear filters button, dynamic result update)

**Checkpoint**: User Stories 1-5 all functional — full European Investment Options feature complete

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T043 [P] Add multi-currency normalization to investment option service in app/services/investment_option_service.py (convert all prices to BASE_CURRENCY using exchange rates, display original currency alongside)
- [x] T044 [P] Add currency display toggle to European investment options view in app/ui/eu_investments.py (show original currency vs base currency, exchange rate indicator)
- [x] T045 [P] Add delisted/suspended ticker handling to investment option service in app/services/investment_option_service.py (detect delisted tickers, flag with badge, exclude from benefit scoring)
- [x] T046 [P] Add weekend/holiday awareness to investment option service in app/services/investment_option_service.py (show last trading day data, indicate market closed status)
- [x] T047 [P] Add unit tests for currency conversion in tests/unit/test_investment_option_service.py (test EUR/USD/GBP/CHF conversions, test base currency configuration)
- [x] T048 [P] Add unit tests for edge cases in tests/unit/test_investment_option_service.py (test delisted ticker handling, test partial data fallback, test offline caching)
- [x] T049 [P] Add integration test for EU price history retrieval in tests/integration/test_price_repository.py (test 5-year history for EU ticker persists and retrieves correctly)
- [x] T050 Code cleanup and refactoring (verify function < 30 lines, files < 400 lines, cyclomatic complexity < 10 per constitution)
- [x] T051 Update README.md with European investment options documentation (supported exchanges, currency configuration, ticker format reference)
- [x] T052 Security hardening: verify EU ticker data has no injection vectors, input validation on search/filter, no secrets in curated data files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (Overview), US2 (Charts), US3 (Rankings) are all P1 and can proceed in parallel
  - US4 (Add to Portfolio) and US5 (Filter/Search) are P2 and depend on US1 being complete
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1 — Overview)**: Can start after Foundational — No dependencies on other stories
- **User Story 2 (P1 — Charts)**: Can start after Foundational — Uses US1 service layer but charts are independently testable
- **User Story 3 (P1 — Rankings)**: Can start after Foundational — Can parallelize with US1 and US2
- **User Story 4 (P2 — Add to Portfolio)**: Depends on US1 (needs option cards and HoldingRepository integration)
- **User Story 5 (P2 — Filter/Search)**: Depends on US1 (needs full options list rendered first)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD — Constitution Principle II)
- Data models before services
- Services before UI views
- Core implementation before integration into dashboard/main.py
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational dataclass tasks (T004-T008) can run in parallel
- US1, US2, and US3 can be developed in parallel (all P1, minimal cross-dependency)
- All tests for a story marked [P] can run in parallel
- Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD — write first, verify they fail):
Task: "Unit test for loading ticker universe in tests/unit/test_investment_option_service.py"
Task: "Unit test for fetching current prices for EU tickers in tests/unit/test_investment_option_service.py"
Task: "Unit test for categorization in tests/unit/test_investment_option_service.py"

# Then implement sequentially (component before view):
Task: "Create European investment options UI component in app/ui/components/investment_option_card.py"
Task: "Create European investment options view in app/ui/eu_investments.py"
Task: "Add European Investment Options section to dashboard in app/ui/dashboard.py"
Task: "Add navigation entry in app/main.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (European Investment Options Overview)
4. **STOP and VALIDATE**: Launch app, verify EU stocks/ETFs/bonds display with current prices
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP — EU options visible on startup!)
3. Add User Story 2 (Charts) + User Story 3 (Rankings) → Test independently → Deploy/Demo
4. Add User Story 4 (Add to Portfolio) + User Story 5 (Filter/Search) → Test independently → Deploy/Demo
5. Complete Polish phase → Full feature

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Overview + Dashboard integration)
   - Developer B: User Story 2 (Performance Deltas + Charts)
   - Developer C: User Story 3 (Benefit Score + Rankings)
3. After P1 stories:
   - Developer A: User Story 4 (Add to Portfolio)
   - Developer B: User Story 5 (Filter/Search)
4. After P2 stories:
   - All developers: Polish phase tasks

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
- yfinance already supports European exchange tickers (.DE, .AS, .PA, .L, .MI, .SW, .ST) — no new API keys needed
- Existing chart_service.py and Plotly integration can be reused for EU option charts

# Feature Specification: European Market Investment Options

**Feature Branch**: `002-eu-investment-options`

**Created**: 2026-07-11

**Status**: Draft

**Input**: User description: "We want to include an overview of stocks, bonds and ETFs for the European market for investment options. It should be feature complete in that it should have the current value delta from previous years - up to 5 years with the corresponding graphs. It should be sorted from the most to least beneficial."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - View European Investment Options Overview (Priority: P1)

As a user, when I open the application, I want to see a curated overview of European investment options across stocks, bonds, and ETFs so I can immediately assess available opportunities in the European market without leaving the dashboard.

**Why this priority**: This is the core feature. The overview is the entry point for discovering investment options and must be visible when the app starts. Without it, the user has no way to explore European market opportunities.

**Independent Test**: Launch the application and verify the European Investment Options section loads with categorized lists of stocks, ETFs, and bond ETFs — each showing current price, name, and asset class. No portfolio holdings are required.

**Acceptance Scenarios**:

1. **Given** the user opens the application, **When** the dashboard loads, **Then** the European Investment Options section is displayed prominently with three clearly labeled categories: Stocks, ETFs, and Bond ETFs.
2. **Given** the investment options section is visible, **When** the user views the stock category, **Then** they see a list of major European stocks across exchanges (XETRA, Euronext, London, Milan, Zurich) with current price and asset class label.
3. **Given** the investment options section is visible, **When** the user views the ETF category, **Then** they see a list of popular European UCITS ETFs with current price and asset class label.
4. **Given** the investment options section is visible, **When** the user views the bond category, **Then** they see a list of European bond ETFs (government and corporate) with current price and asset class label.
5. **Given** market data is unavailable (offline/API error), **When** the investment options section loads, **Then** the user sees cached/last-known data with a clear staleness indicator and the timestamp of the last successful update.

---

### User Story 2 - View 5-Year Performance Delta & Charts (Priority: P1)

As a user, I want to see the performance delta (price change over time) for each investment option over the past 1, 3, and 5 years along with interactive charts, so I can evaluate long-term trends before making investment decisions.

**Why this priority**: Performance history and charts are essential for the user to evaluate investment quality. Without multi-year data, the user cannot assess whether an option is worth pursuing. This is co-equal priority with the overview because the feature is incomplete without it.

**Independent Test**: Navigate to the European Investment Options section and select any investment option. Verify that 1-year, 3-year, and 5-year performance deltas are displayed with percentage change and absolute change. Verify interactive charts render for each time period.

**Acceptance Scenarios**:

1. **Given** an investment option is displayed in the overview, **When** the user views its details, **Then** the option shows its current price alongside its 1-year, 3-year, and 5-year price change (both absolute and percentage).
2. **Given** an investment option's performance data is visible, **When** the user selects a time period (1Y, 3Y, 5Y), **Then** an interactive price chart renders showing the historical price trend for that period.
3. **Given** a chart is displayed, **When** the user hovers over a data point, **Then** they see the exact price, date, and percentage change from the starting point.
4. **Given** insufficient historical data exists for a selected time period (e.g., a recently listed ETF), **When** the chart renders, **Then** it shows all available data up to the listing date without fabricating data points and displays a note about the available data range.
5. **Given** a data point is displayed, **When** the value is positive, **Then** it is shown in green; when negative, it is shown in red — following the existing color convention in the application.

---

### User Story 3 - View Sorted Rankings by Benefit (Priority: P1)

As a user, I want the investment options to be sorted from most to least beneficial based on a composite score, so I can quickly identify the best opportunities without manually comparing each option.

**Why this priority**: Sorting is what transforms a raw list into actionable intelligence. Without it, the user must manually compare dozens of options, defeating the purpose of the overview.

**Independent Test**: Navigate to the European Investment Options section and verify that options within each category (Stocks, ETFs, Bonds) are sorted by a benefit score in descending order. Verify the sort order changes when the user selects a different ranking criteria.

**Acceptance Scenarios**:

1. **Given** the investment options are displayed, **When** the user views any category, **Then** options are sorted from highest to lowest benefit score by default.
2. **Given** the benefit score is displayed, **When** the user examines the ranking, **Then** they can see the individual factors contributing to the score (e.g., performance trend, volatility, volume).
3. **Given** the default sort is by benefit score, **When** the user selects an alternative sort criterion (e.g., "Highest 5Y Return", "Lowest Volatility", "Most Traded"), **Then** the list re-sorts accordingly.
4. **Given** options from different asset classes are displayed, **When** the user views the full overview, **Then** each asset class section is independently sortable.

---

### User Story 4 - Add Investment Option to Portfolio (Priority: P2)

As a user, I want to add any investment option from the European overview directly to my portfolio, so I can seamlessly act on opportunities I discover.

**Why this priority**: This connects the discovery feature to the existing portfolio management workflow. It is important but depends on Stories 1-3 being in place first.

**Independent Test**: From the European Investment Options section, click "Add to Portfolio" on any option and verify it appears in the Holdings page with the correct ticker, current price, and zero gain/loss.

**Acceptance Scenarios**:

1. **Given** an investment option is displayed in the overview, **When** the user clicks "Add to Portfolio", **Then** a form pre-fills the ticker symbol and current price, allowing the user to enter quantity and purchase price.
2. **Given** the user submits the add form with valid data, **When** the holding is saved, **Then** the option appears in the Holdings page and the "Add to Portfolio" button changes to "In Portfolio" (disabled).
3. **Given** the user enters an invalid quantity or purchase price, **When** they attempt to submit, **Then** they see a clear validation error and the holding is not added.

---

### User Story 5 - Filter and Search Investment Options (Priority: P2)

As a user, I want to filter and search within the European investment options so I can quickly find specific investments by name, ticker, exchange, or sector.

**Why this priority**: With dozens of options across categories, filtering is essential for efficient navigation. It enhances discoverability but is not required for the core feature to function.

**Independent Test**: Enter a search term (e.g., "SAP" or "Technology") in the filter bar and verify the list narrows to matching results across all categories.

**Acceptance Scenarios**:

1. **Given** the investment options overview is displayed, **When** the user types in the search/filter bar, **Then** the list dynamically filters to show only options whose name, ticker, or sector match the search term.
2. **Given** the user selects a specific exchange filter (e.g., "XETRA only"), **When** the filter is applied, **Then** only options from that exchange are displayed.
3. **Given** the user selects a sector filter (e.g., "Technology"), **When** the filter is applied, **Then** only options in the Technology sector are displayed.
4. **Given** multiple filters are active, **When** the user clears a filter, **Then** the previously filtered results are restored correctly.

---

### Edge Cases

- What happens when a European ticker has no data for a requested time period (e.g., newly listed ETF with only 6 months of history)? The system MUST display available data with a note indicating the data range is shorter than requested.
- How does the system handle currency differences across European exchanges (EUR, GBP, CHF, SEK)? The system MUST normalize all values to the user's configured base currency using current exchange rates and display the original currency alongside.
- What happens when the market data provider is rate-limited or returns partial results? The system MUST display whatever data was successfully fetched and clearly indicate which options have stale or missing data.
- What happens when a ticker is delisted or suspended? The system MUST flag it with a "Suspended/Delisted" badge and exclude it from benefit scoring while still showing historical data if available.
- How does the system handle weekends and public holidays when markets are closed? The system MUST show the last available market data and indicate when the market was last open.
- What happens when 5-year historical data is unavailable for a specific instrument? The system MUST fall back to the maximum available history (e.g., 3 years for a 3-year-old ETF) and note the available range.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST display a European Investment Options section on the application's main dashboard/landing view, visible immediately on startup.
- **FR-002**: System MUST categorize investment options into three distinct groups: European Stocks, European ETFs, and European Bond ETFs.
- **FR-003**: System MUST display current price, currency, and exchange information for each investment option.
- **FR-004**: System MUST calculate and display 1-year, 3-year, and 5-year performance deltas (absolute change and percentage) for each option.
- **FR-005**: System MUST render interactive price charts for each option supporting 1Y, 3Y, and 5Y time periods.
- **FR-006**: System MUST sort options within each category by a composite benefit score (combining trend momentum, volume, and historical return) in descending order by default.
- **FR-007**: System MUST allow the user to change the sort criterion (benefit score, highest return, lowest volatility, most traded).
- **FR-008**: System MUST support adding any European investment option directly to the user's portfolio from the overview.
- **FR-009**: System MUST provide search and filter capabilities (by name, ticker, exchange, sector) across all categories.
- **FR-010**: System MUST normalize all displayed values to a single base currency (EUR default, configurable) and show original currency alongside.
- **FR-011**: System MUST cache market data locally and serve stale data when the API is unreachable, with clear staleness indicators.
- **FR-012**: System MUST cover major European exchanges: XETRA (Germany), Euronext Amsterdam, Euronext Paris, Euronext Brussels, London Stock Exchange, Borsa Italiana, SIX Swiss Exchange, and NASDAQ Stockholm.
- **FR-013**: System MUST include a curated list of approximately 20-30 European stocks across sectors (Technology, Healthcare, Consumer, Finance, Energy, Industrials).
- **FR-014**: System MUST include a curated list of approximately 10-15 European UCITS ETFs (broad market, sector-specific, emerging markets).
- **FR-015**: System MUST include a curated list of approximately 8-12 European bond ETFs (government bonds, corporate bonds, inflation-linked, EUR-hedged).
- **FR-016**: System MUST handle missing or incomplete historical data gracefully — showing available data and noting the data range.
- **FR-017**: System MUST handle delisted or suspended tickers by flagging them and excluding from benefit scoring.

### Key Entities

- **InvestmentOption**: Represents a single European investment opportunity — ticker symbol, name, exchange, asset class (stock/ETF/bond ETF), sector, current price, currency, and historical price data. Tracks derived values: 1Y/3Y/5Y performance deltas, benefit score, and ranking position.
- **BenefitScore**: A composite ranking metric for an investment option — combines trend momentum, historical return, and volume into a single score. Configurable weighting factors.
- **PerformanceDelta**: A time-period-specific performance record — start date, end date, start price, end price, absolute change, percentage change. Supports 1Y, 3Y, and 5Y periods.
- **BondMarketContext**: European bond market overview — ECB deposit rate, Eurozone government bond yields (2Y, 5Y, 10Y, 30Y), yield curve shape (normal/inverted/flat). Used to contextualize bond ETF recommendations.
- **ExchangeRate**: Currency conversion record — source currency, target (base) currency, rate, timestamp. Used for normalizing multi-currency values to the user's preferred currency.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: European Investment Options section loads and displays all categorized options with current prices within 5 seconds of app launch.
- **SC-002**: 5-year historical price charts render within 3 seconds for any selected option.
- **SC-003**: User can filter/search the investment options list and see results update within 1 second.
- **SC-004**: Adding an investment option to the portfolio completes within 3 seconds and the option appears in the Holdings page immediately.
- **SC-005**: Application remains fully functional for viewing cached investment options when offline, with no errors or crashes.
- **SC-006**: 100% of displayed investment options have valid, non-stale price data after a successful refresh (staleness threshold: 1 hour during market hours).
- **SC-007**: Benefit score ranking produces a stable, deterministic sort order for identical inputs.
- **SC-008**: All currency conversions are accurate to within 0.1% of the real exchange rate at the time of the last data fetch.

## Assumptions

- The application will continue to run as a single-user, local desktop application — no multi-user or server component.
- The European market data will be sourced from a provider that supports European exchange tickers (e.g., Yahoo Finance via yfinance, which covers XETRA, Euronext, LSE, etc. with exchange-suffixed ticker symbols).
- The curated list of European investment options will be maintained as a static configuration file that can be manually updated — no automated discovery of new listings is required for v1.
- Currency exchange rates for normalization will be fetched from the same market data provider (EUR/USD, GBP/EUR, CHF/EUR, etc.) or a free exchange rate API.
- The user's base currency defaults to EUR but is configurable to other currencies (USD, GBP, CHF).
- Bond ETF data (government and corporate bond ETFs traded on European exchanges) is sufficient to represent the bond market — individual bond pricing is out of scope for v1.
- The benefit score algorithm uses equal weighting of momentum (40%), historical return (40%), and volume (20%) by default, with the weights being configurable in future versions.
- Existing application architecture (provider pattern, repository pattern, service layer) will be reused and extended rather than replaced.

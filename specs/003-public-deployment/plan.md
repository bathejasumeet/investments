# Public Deployment Plan

**Branch**: `[003-public-deployment]` | **Date**: 2026-08-02 | **Status**: Planning

**Scope**: Make the Investment Portfolio Planner & Tracker accessible over the internet as a privacy-conscious, multi-user application rather than a local single-user app.

## Summary

The current application is a local Streamlit application backed by SQLite and yfinance. It is not safe to expose publicly in its current form: it has no authentication, no user ownership on persisted portfolio data, local-file configuration, local SQLite storage, page-level infrastructure construction, and no production deployment or operational controls.

The recommended first public architecture is a **containerized modular monolith**:

- Streamlit remains the presentation layer for the first public release.
- A managed OIDC identity provider handles authentication; application code owns authorization and data isolation.
- PostgreSQL replaces SQLite for production persistence.
- Alembic remains the schema migration tool.
- A single application composition root constructs services and repositories.
- A shared market-data facade controls caching, rate limits, freshness, and provider failures.
- A scheduled worker or platform job refreshes broad market data outside user page renders.
- Managed backups, error monitoring, logging, and secret storage are required before launch.

Do not expose the current app directly and call it production. A public demo with no persisted personal data is a smaller, separate target; this plan assumes users can create accounts and store real portfolio information.

## Current Baseline

The repository already has some useful foundations:

- Alembic migrations and an automatic legacy-database upgrade path exist in `migrations/` and `app/database.py`.
- Historical price writes now avoid duplicate ticker/date rows.
- The UI, services, repositories, models, and provider are separated into recognizable layers.
- Unit, integration, and end-to-end test directories exist.

The following public-deployment gaps remain:

- `app/main.py` still initializes the database on Streamlit startup and routes directly to page functions.
- UI modules construct `get_session()`, repositories, and `YFinanceProvider` directly; there is no application composition root.
- `app/config.py` loads `data/.env` and defaults to `data/portfolio.db`, which is appropriate for local development but not a managed production environment.
- The schema has no user, account, tenant, or ownership boundary. `Holding`, `Goal`, and `FourFundPlan` rows are currently globally visible to any application session.
- `app/models/holding.py` represents one aggregate position per ticker and does not model accounts, transactions, tax lots, sales, dividends, or per-user currency context.
- `MarketDataProvider` and `YFinanceProvider` perform external network I/O during page workflows. yfinance has no production SLA, quota contract, or guaranteed data availability for a public product.
- `MarketDataService` is not yet the single market-data path; some services call the provider directly and cached values need explicit source-currency semantics.
- `.streamlit/config.toml` is a development configuration and has no documented production security/proxy configuration.
- No container definition, deployment manifest, CI workflow, secret-manager integration, health/readiness check, monitoring setup, backup runbook, or incident runbook is present.
- The current E2E tests compose Python services directly rather than verifying authenticated browser workflows or cross-user isolation.

## Launch Tiers

Use these tiers to avoid confusing a public demo with a public financial-data service.

### Tier A: Public demo

A read-only or disposable demo with synthetic/sample data, no real user portfolios, no account creation, and no expectation of data durability. This can be deployed sooner, but it must not accept personal financial data.

### Tier B: Public multi-user beta

Authenticated users can create portfolios, goals, and saved plans. Data is isolated per user, production data is backed up, provider failures are visible, and a small invite-only cohort exercises the system.

### Tier C: General public release

Tier B plus documented privacy/terms, deletion/export workflows, security review, operational alerting, restore drills, load testing, provider/legal review, and a rollback-tested release process.

**Target for this plan**: Tier B first, followed by Tier C. Tier A may be used as an interim deployment only when all persisted data is synthetic or disposable.

## Target Architecture

```text
Browser
  -> HTTPS reverse proxy / hosting platform
  -> Managed OIDC authentication
  -> Streamlit application container
       -> Application composition root
            -> Use cases / query services
                 -> User-scoped repositories -> PostgreSQL
                 -> Shared market-data facade -> cache -> licensed provider(s)
       -> Structured logs / error monitoring / metrics

Scheduled platform job or worker
  -> market-data refresh facade
  -> shared cache and PostgreSQL price history

Managed backup service
  -> encrypted PostgreSQL backups and restore drills
```

Keep this as a modular monolith initially. Do not introduce microservices, a public REST API, CQRS infrastructure, or distributed job infrastructure until measured usage requires them.

## P0 Launch Blockers

These must be complete before accepting real user data or advertising the service publicly.

- [ ] Choose the launch tier and write down whether the product is a demo, invite-only beta, or general public service.
- [ ] Define the threat model and data classification for portfolio holdings, goals, transaction values, email addresses, provider responses, logs, and backups.
- [ ] Add managed authentication using OIDC/OAuth, magic link, or a hosted identity provider. Do not implement password storage or password reset flows from scratch.
- [ ] Add a `User` identity model and an ownership boundary for every user-owned record: holdings, goals, goal mappings through their parents, and saved four-fund plans. Shared market-data cache rows must remain separate from user data.
- [ ] Enforce ownership in application use cases and repositories, not only in Streamlit widgets. Every read, update, delete, and add-to-portfolio command must receive the authenticated user identity and scope its query.
- [ ] Add authorization tests proving that user A cannot read, update, delete, or infer user B's holdings, goals, mappings, or saved plans, including guessed IDs and stale Streamlit session state.
- [ ] Replace production SQLite with managed PostgreSQL. Keep SQLite only for local development and isolated unit tests.
- [ ] Define a production `DATABASE_URL` with TLS/SSL requirements, connection pooling, connection limits, and migration ownership. Do not use a local filesystem path as the production database configuration.
- [ ] Run `alembic upgrade head` as a release/deploy step before application instances start. Do not run arbitrary schema upgrades on every Streamlit rerun or concurrently from multiple replicas.
- [ ] Back up the current local database before any migration or public deployment. Test restoring a backup into a clean database and verify row counts and representative portfolio values.
- [ ] Move secrets to the hosting platform's secret manager. Do not load production secrets from a committed or mounted `data/.env` file; rotate any credential that has ever been exposed.
- [ ] Review the data provider's terms, redistribution rules, rate limits, and commercial/public-use permissions. Replace or supplement yfinance if its terms or reliability are insufficient for the intended audience.
- [ ] Add explicit stale, unavailable, rate-limited, and provider-error states. Never represent missing market data as a zero-valued price or silently present it as current.
- [ ] Establish HTTPS, a real domain, secure authentication cookies/session handling, trusted proxy configuration, and a documented logout flow.
- [ ] Add production error monitoring, structured logs, alerts for database/provider failures, and a named on-call/incident owner before beta access.
- [ ] Provide account deletion and data export before storing real user portfolios. Define retention and backup-deletion behavior for deleted accounts.

## Phase 0: Product, Legal, and Hosting Decisions

- [ ] Decide the supported countries, currencies, and languages for the first release.
- [ ] Decide whether the app is informational/planning software or may be interpreted as personalized investment advice. Obtain legal review for the disclaimer and product claims.
- [ ] Decide whether users may store actual holdings and cost basis, or only hypothetical portfolios, during beta.
- [ ] Define the minimum user identity fields required. Prefer an opaque provider subject ID and verified email over collecting unnecessary profile data.
- [ ] Choose the hosting model: managed container platform, Streamlit Community Cloud with an external database, or a cloud VM/container service. Record its limits for websockets, session affinity, persistent storage, private networking, and secrets.
- [ ] Choose the identity provider and document callback URLs, allowed origins, logout URLs, token/session lifetime, MFA options, and account recovery behavior.
- [ ] Choose the managed PostgreSQL provider, region, encryption configuration, backup retention, point-in-time recovery, maintenance windows, and service limits.
- [ ] Define target scale: expected registered users, concurrent sessions, market-data tickers per refresh, database size, and peak refresh activity.
- [ ] Define service objectives: target availability, maximum acceptable stale-data age, recovery time objective, and recovery point objective.
- [ ] Create a short architecture decision record covering the above choices and the reason Streamlit remains the initial UI architecture.

## Phase 1: Production Configuration and Application Bootstrap

### Configuration and secrets

- [ ] Refactor `app/config.py` so production configuration is supplied explicitly by environment variables or a secret manager; load `data/.env` only under an explicit local-development mode.
- [ ] Replace `DB_PATH` with a validated `DATABASE_URL` for production while retaining a clearly documented SQLite local default.
- [ ] Validate required settings at startup: environment name, database URL, allowed host/origin, OIDC settings, base currency, provider selection, cache policy, and log level.
- [ ] Fail fast with a safe operator-facing error when required configuration is missing. Never include secret values, tokens, connection strings, or user data in the error.
- [ ] Separate development, staging, and production configuration. Prevent a production process from accidentally pointing at a developer database or test provider.
- [ ] Add a sanitized configuration diagnostic that reports selected provider, database host name, environment, and feature flags without exposing credentials.

### Composition and lifecycle

- [ ] Add an application composition root, for example `app/bootstrap.py`, that constructs the database engine/session factory, provider adapter, repositories, cache facade, and use cases.
- [ ] Refactor `app/main.py` and every module in `app/ui/` to consume injected application services. Remove direct construction of `YFinanceProvider`, repositories, and production sessions from page functions.
- [ ] Keep Streamlit `session_state` limited to presentation state such as filters, selected tabs, and pending form actions. It is not an authentication or authorization boundary.
- [ ] Add a request/session scope that closes database sessions reliably after each Streamlit interaction and rolls back failed mutations.
- [ ] Add a unit-of-work or transaction scope so a multi-step command commits once and rolls back as a unit. Repositories should not independently commit changes.
- [ ] Ensure the application can be instantiated in tests with an in-memory/test PostgreSQL database, fake identity, and deterministic market-data ports.

### Container and runtime

- [ ] Add a production `Dockerfile` with a pinned base image, reproducible dependency installation, a non-root runtime user, no development tools, and a documented exposed port.
- [ ] Add `.dockerignore` excluding `.git`, `.venv`, caches, local databases, local environment files, test artifacts, and editor files.
- [ ] Add a lock or constraints strategy so production dependencies are reproducible. Review direct and transitive dependency licenses and vulnerabilities.
- [ ] Set the container timezone and locale deliberately; use timezone-aware UTC timestamps in application and database boundaries.
- [ ] Configure graceful shutdown and connection cleanup. Confirm that Streamlit sessions do not leave database connections or worker threads behind.
- [ ] Add a container startup smoke test that imports the application, loads validated configuration, connects to the database, and verifies the migration revision.
- [ ] Configure the hosting platform's health/readiness checks using a supported Streamlit health endpoint or a small separate health process. Do not treat a running TCP port as readiness.
- [ ] Separate migration execution from web-process startup in the deployment definition.

### Streamlit and proxy configuration

- [ ] Create production-specific Streamlit configuration. Disable development-only settings such as `runOnSave` and review server address, port, websocket, XSRF, CORS, and proxy settings.
- [ ] Put TLS termination and security headers at the managed reverse proxy or hosting platform. Verify HTTPS redirects, HSTS, clickjacking protection, content-type sniffing protection, and an appropriate content security policy where compatible with Streamlit.
- [ ] Restrict allowed hosts and origins. Verify that websocket connections work only through the intended domain.
- [ ] Define maximum request/session timeouts and user-facing behavior for long-running Monte Carlo and market-data operations.
- [ ] Verify that uploaded files, if added later, are size-limited, type-validated, malware-scanned where appropriate, and stored outside the application container.

## Phase 2: Identity, Authorization, and User Data Isolation

- [ ] Add a `users` table keyed by the identity-provider subject, with created/updated timestamps, status, and minimal profile fields.
- [ ] Add ownership columns and indexes to user-owned tables. At minimum, cover `holdings`, `goals`, and `four_fund_plans`; ensure `goal_holding_mappings` can only connect rows owned by the same user.
- [ ] Decide whether the first release supports one portfolio per user or multiple accounts per user. If multiple accounts are needed, add an `accounts` table and scope holdings/goals/plans through it.
- [ ] Add foreign keys, uniqueness constraints, and migration backfill rules for existing local data. Existing personal data must be explicitly assigned to an owner during import rather than silently becoming globally visible.
- [ ] Implement an authenticated-user context at the application boundary. UI code must not be allowed to choose an arbitrary owner ID.
- [ ] Centralize authorization checks in use cases/repositories. Test direct method calls as well as normal UI paths.
- [ ] Verify authorization on error paths, cached responses, export/download paths, and recommendation/add-to-portfolio actions.
- [ ] Add account lifecycle workflows: first-login provisioning, logout, session expiry, disabled account behavior, account deletion, and data export.
- [ ] Configure secure session/token handling through the chosen identity provider. Verify expiry, refresh, logout invalidation, replay resistance, and CSRF/XSRF behavior for the selected hosting topology.
- [ ] Add rate limits and abuse controls for login callbacks, refresh actions, ticker validation, recommendation generation, and expensive Monte Carlo simulations.
- [ ] Add audit events for sign-in, account deletion/export, portfolio mutations, administrative access, and migration/import operations. Keep logs free of quantities and sensitive financial values unless explicitly justified.

## Phase 3: Production Persistence and Financial Data Model

- [ ] Create a PostgreSQL schema target and run all migrations against PostgreSQL in CI and staging. Do not rely only on SQLite behavior.
- [ ] Enable and test foreign-key enforcement, transaction isolation, indexes, and cascade behavior in PostgreSQL.
- [ ] Add a safe migration path from the existing single-user SQLite database to an explicitly selected user/account. Include a dry-run report and row-count/value checks.
- [ ] Decide whether the MVP keeps one aggregate holding per ticker or moves to accounts and transactions. Document the choice before adding users.
- [ ] If keeping aggregate holdings for beta, enforce uniqueness per owner/account rather than globally and document that multiple tax lots/sales are not yet modeled.
- [ ] If supporting real portfolio accounting, introduce transaction records for buys, sells, dividends, fees, and transfers, then derive positions and cost basis rather than overwriting a single average price.
- [ ] Replace financial `Float` columns with a currency-aware money representation using `Decimal` or an equivalent fixed-precision database type. Preserve currency alongside every monetary value.
- [ ] Normalize all persisted and compared timestamps to timezone-aware UTC. Define how market close dates, weekends, holidays, and provider timestamps are represented.
- [ ] Add source currency, conversion rate, conversion timestamp, and data source metadata to cached quotes/history where needed. Do not infer USD for history when the provider did not supply a currency.
- [ ] Add idempotent cache writes and retention policies for `price_points`. Define which history is durable, how much is retained, and how old data is compacted.
- [ ] Add indexes for every user-scoped query and verify query plans for dashboard, holdings, goals, and plan listing.
- [ ] Configure connection pooling, statement timeouts, maximum connections, and database-level least privilege for the application role.
- [ ] Encrypt production database storage and backups. Restrict network access to the application and migration jobs.
- [ ] Configure automated backups and point-in-time recovery. Perform and document a restore drill before beta.

## Phase 4: Market Data, Caching, and Background Work

- [ ] Review whether yfinance is permitted and reliable for public/commercial use. Select a provider with documented terms, quota behavior, and support appropriate to the target tier.
- [ ] Split `MarketDataProvider` into narrow ports for quotes/history, FX, fund metadata, and discovery. Keep provider-specific behavior inside adapters.
- [ ] Make `MarketDataService` or its replacement the only path for current prices, history, currency conversion, freshness, and stale fallback.
- [ ] Define cache policy by data type: quote TTL, history refresh interval, FX TTL, provider failure fallback duration, and maximum stale age.
- [ ] Use a shared cache for multiple app instances when needed. Do not rely on per-process memory or Streamlit session state for cross-user consistency.
- [ ] Add provider rate limiting, request deduplication, exponential backoff with jitter, bounded concurrency, and a circuit breaker or equivalent outage control.
- [ ] Add provider contract tests with recorded deterministic responses for missing prices, invalid tickers, GBp/pence normalization, currency conversion, stale data, timeouts, rate limits, and partial bulk results.
- [ ] Move broad EU universe refreshes and other expensive fetches to a scheduled job or controlled background worker. User page renders should read prepared/cacheable data where possible.
- [ ] Make refresh operations idempotent and safe when two users or workers request the same ticker simultaneously.
- [ ] Add provider attribution and an `as of` timestamp to user-visible market data. Make it clear that quotes may be delayed and are not guaranteed execution prices.
- [ ] Define behavior when the provider is unavailable for a prolonged period: stale read-only mode, retry schedule, operator alert, and user messaging.
- [ ] Bound recommendation and Monte Carlo work per user. Add cancellation, queueing, or progress behavior that does not tie up all web workers.

## Phase 5: Security, Privacy, and Trust

- [ ] Run a threat model covering account takeover, IDOR, session fixation/replay, secret leakage, prompt/data injection if AI is ever added, provider abuse, denial of service, and malicious ticker/name inputs.
- [ ] Validate and normalize every external input: identity claims, ticker symbols, quantities, prices, dates, goal names, search/filter values, sort values, and import files.
- [ ] Review all dynamic `st.markdown` and HTML/CSS rendering for injection or unsafe content. Escape or constrain user-controlled names and values.
- [ ] Ensure exceptions shown to users are generic and actionable; send detailed stack traces only to protected monitoring.
- [ ] Run dependency vulnerability and license scans on every push and before release. Generate an SBOM for the production artifact.
- [ ] Run static analysis, secret scanning, and container image scanning in CI. Block high/critical findings unless explicitly accepted and tracked.
- [ ] Use least-privilege service accounts for the app, migrations, database, identity provider, backups, and monitoring.
- [ ] Keep credentials out of source control, Docker layers, logs, crash reports, analytics payloads, and test fixtures. Rotate credentials and document the rotation procedure.
- [ ] Encrypt data in transit and at rest. Document encryption boundaries and key ownership.
- [ ] Publish a privacy policy, terms of service, cookie/session disclosure, market-data disclosure, and investment-risk disclaimer reviewed for the launch jurisdictions.
- [ ] Define data-subject workflows appropriate to the target jurisdictions: consent where required, access/export, correction, deletion, retention, and backup purge windows.
- [ ] Define an incident response process for account compromise, data exposure, provider misuse, and database corruption. Include notification responsibilities and evidence preservation.
- [ ] Decide whether a security contact and vulnerability disclosure process should be public.

## Phase 6: Testing and CI/CD

### Test coverage

- [ ] Add configuration tests for development, staging, production, missing secrets, invalid URLs, and unsafe defaults.
- [ ] Add migration tests for an empty PostgreSQL database, the current SQLite schema, legacy duplicate price rows, repeated upgrades, downgrade policy, and backup restore.
- [ ] Add repository/use-case tests proving transaction rollback and ownership filtering.
- [ ] Add cross-user authorization tests for every user-owned aggregate and command.
- [ ] Add provider contract tests using replayed fixtures. Keep live provider tests opt-in and excluded from the deterministic default suite.
- [ ] Add tests for stale-data behavior, cache invalidation, partial provider results, rate limiting, and concurrent refreshes.
- [ ] Add Streamlit `AppTest` or browser-level tests for login/session provisioning, add/edit/delete holding, goal mapping, EU option refresh/filter/add, plan save/load/delete, logout, and error states.
- [ ] Add accessibility checks for keyboard navigation, labels, contrast, non-color status cues, responsive layouts, and screen-reader-friendly controls.
- [ ] Add performance tests for concurrent dashboard loads, EU refresh, recommendations, charts, and Monte Carlo limits. Record provider and database latency budgets.
- [ ] Add a smoke test against the staging deployment after every release.

### CI and release pipeline

- [ ] Add CI workflows for formatting, Ruff lint, pytest, coverage threshold, type checking, dependency audit, secret scanning, and container scanning.
- [ ] Resolve or explicitly pin the current NumPy/mypy compatibility issue before making mypy a required production gate.
- [ ] Build the production container once per commit and promote the same immutable artifact through staging to production.
- [ ] Run migrations as an explicit, auditable release job. Fail the deployment if migration or schema verification fails.
- [ ] Use environment protection and approval for production deployment and database migrations.
- [ ] Publish a versioned release identifier into the app diagnostics and logs.
- [ ] Verify rollback behavior for application versions. Maintain backward-compatible database migrations when two versions may overlap during rollout.
- [ ] Never run tests against real user data or production credentials. Use synthetic fixtures and isolated staging resources.

## Phase 7: Observability and Operations

- [ ] Emit structured logs with request/session correlation IDs, deployment version, user-safe identity hash, operation name, latency, result status, and provider/database outcome.
- [ ] Do not log portfolio quantities, purchase prices, goal amounts, access tokens, email addresses, or raw provider payloads by default.
- [ ] Track metrics for authentication failures, active sessions, page/action latency, database errors, migration status, provider latency/error/rate-limit counts, stale data age, cache hit rate, and background job failures.
- [ ] Configure alerts with thresholds and owners for database unavailability, migration failure, provider outage, high stale-data age, authentication anomalies, and resource exhaustion.
- [ ] Add an operator runbook for deploy, rollback, migration failure, database restore, secret rotation, provider outage, account lockout, and incident escalation.
- [ ] Set resource limits and autoscaling/concurrency policy for the application container. Test behavior when the provider or database is slow.
- [ ] Define backup retention and verify that deleted-user data is handled according to the retention policy.
- [ ] Perform a disaster-recovery exercise and record actual restore time against the target RTO/RPO.
- [ ] Add uptime and synthetic user-journey monitoring from outside the hosting environment.

## Phase 8: Public UX and Documentation

- [ ] Remove local-only language such as `Local single-user mode` from `app/main.py` and update all onboarding copy for authenticated users.
- [ ] Add sign-in, sign-out, first-login provisioning, session-expired, unauthorized, and account-disabled states.
- [ ] Add onboarding that explains what data is stored, how market data is sourced, how stale values are shown, and how to delete/export the account.
- [ ] Show currency, source, timestamp, and delayed/stale status consistently across dashboard, goals, charts, recommendations, EU options, and four-fund plans.
- [ ] Ensure empty, loading, error, stale, partial-data, and success states are usable on mobile and desktop.
- [ ] Review all forms for validation, accessible labels, keyboard operation, confirmation for destructive actions, and safe recovery after a failed write.
- [ ] Add an in-app link to privacy, terms, risk disclosure, support, status, and data-management pages.
- [ ] Update `README.md` with production architecture, local-vs-production setup, migration commands, environment variables, security assumptions, provider limitations, and operator runbooks.
- [ ] Add a public `SECURITY.md` with supported versions and a security contact if the repository or product is public.
- [ ] Add a production quickstart for staging deployment and a separate local development quickstart.

## Phased Delivery

### Milestone 1: Safe staging foundation

- [ ] Choose hosting, identity provider, PostgreSQL, secrets, monitoring, and domain.
- [ ] Add production configuration validation and composition root.
- [ ] Add Dockerfile, CI, staging deployment, migration job, health checks, and smoke tests.
- [ ] Deploy a synthetic-data staging environment with no real user data.

### Milestone 2: Multi-user beta

- [ ] Add authentication and user-scoped schema/use cases.
- [ ] Add authorization and cross-user isolation tests.
- [ ] Add account export/deletion, privacy/risk documents, backups, restore drill, and incident runbook.
- [ ] Add provider contract/caching/rate-limit controls and beta quotas.
- [ ] Invite a small cohort and monitor stale-data, latency, error, and support metrics.

### Milestone 3: General public release

- [ ] Complete security review and high-severity remediation.
- [ ] Complete legal/provider review for supported jurisdictions and data sources.
- [ ] Meet defined availability, RTO/RPO, performance, and accessibility targets.
- [ ] Complete disaster-recovery, rollback, secret-rotation, and provider-outage exercises.
- [ ] Publish status, support, privacy, terms, security contact, and risk disclosures.
- [ ] Establish an on-call rotation and release approval process.

## Definition of Done for Public Beta

The beta is ready only when all of the following are true:

- [ ] A new user can authenticate, create an isolated portfolio, use the major workflows, sign out, and sign back in without seeing another user's data.
- [ ] A database restore and migration can be performed by a documented operator using a clean environment.
- [ ] Provider failures produce bounded latency, visible stale/unavailable status, and operator alerts without corrupting portfolio data.
- [ ] Production secrets are held outside source control and can be rotated without rebuilding application code.
- [ ] CI blocks broken tests, formatting/lint failures, type-check failures, high/critical dependency findings, secret leaks, and failed migration tests.
- [ ] Logs and monitoring support diagnosing a failed request without exposing user financial data.
- [ ] Account deletion/export and privacy/risk disclosures are available and tested.
- [ ] The exact container artifact deployed to staging has passed smoke tests and is the artifact promoted to production.

## Open Decisions

- [ ] Is the first public release a synthetic-data demo, an invite-only beta with real data, or a general public service?
- [ ] Which jurisdictions and currencies are supported?
- [ ] Which identity provider will be used?
- [ ] Which hosting platform and managed PostgreSQL service will be used?
- [ ] Is yfinance acceptable for the intended public use, or is a licensed provider required?
- [ ] Does beta support aggregate one-position-per-ticker holdings, or must it support transaction/tax-lot accounting?
- [ ] What are the target availability, stale-data, RTO, RPO, latency, and monthly-cost budgets?
- [ ] Who owns production operations, provider relationships, security incidents, and support?

## Relevant Files

- `app/main.py`: Streamlit entrypoint, routing, current local-only wording, and startup lifecycle.
- `app/config.py`: environment loading and local-file defaults to replace with validated deployment configuration.
- `app/database.py`: engine/session lifecycle and migration entrypoint.
- `migrations/`: schema revisions and production migration process.
- `app/models/`: user ownership, account/transaction, currency, timestamp, and database-constraint changes.
- `app/repositories/`: user-scoped queries, transaction boundaries, and cache persistence.
- `app/services/`: use cases, authorization boundary, market-data facade, and DTO/view-model contracts.
- `app/providers/base.py` and `app/providers/yfinance_provider.py`: narrow provider ports, external-data policy, and adapter behavior.
- `app/ui/`: injected application services, authenticated user context, and public UX states.
- `.streamlit/config.toml`: production Streamlit/proxy configuration review.
- `pyproject.toml`: dependency constraints, test configuration, and CI tooling.
- `tests/conftest.py` and `tests/{unit,integration,contract,e2e}/`: deterministic provider, migration, isolation, UI, and deployment tests.
- `README.md`, `SECURITY.md`, and operator runbooks: public setup, disclosures, and operational documentation.
- `.github/workflows/`, `Dockerfile`, `.dockerignore`, and deployment manifests: reproducible CI/CD and runtime packaging to add.

## Constitution Check

- **Strong Design Patterns**: Pass if authentication, authorization, caching, transactions, and provider adapters are explicit infrastructure/application boundaries rather than conditional UI logic.
- **Test-Driven Development**: Pass if each production deployment capability has failing-first tests for migrations, isolation, provider contracts, security-sensitive commands, and critical user journeys.
- **User Experience Consistency**: Pass if authenticated, unauthorized, stale, unavailable, empty, loading, success, and destructive-action states are defined across all pages.
- **Code Simplicity & Readability**: Pass if the first public release remains a modular monolith and does not add distributed services without measured need.
- **CI/CD Readiness**: Pass only when immutable artifacts, protected releases, migration verification, rollback, backups, monitoring, and security scans are operational.

## Recommended Order

1. Decide launch tier, jurisdictions, identity, hosting, provider, data model, and service objectives.
2. Build production configuration, composition root, PostgreSQL target, container, migration job, CI, and staging.
3. Add authentication and user-scoped ownership before allowing real data.
4. Harden market-data caching, provider contracts, stale/error behavior, and background refresh.
5. Add security/privacy/legal controls, backups, restore drills, observability, and operator runbooks.
6. Run an invite-only beta, measure real bottlenecks, then complete general-public release gates.

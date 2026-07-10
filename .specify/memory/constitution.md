<!--
  Sync Impact Report
  ==================
  Version change: 0.0.0 (initial template) → 1.0.0 (first ratified constitution)
  Modified principles: All — first population from template placeholders
  Added sections:
    - Core Principles (5 principles)
    - Design & Architecture Constraints
    - Development Workflow & Quality Gates
  Removed sections: None
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ aligned (Constitution Check section already references constitution generically)
    - .specify/templates/spec-template.md ✅ aligned (no constitution-specific sections embedded)
    - .specify/templates/tasks-template.md ✅ aligned (TDD flow already in template: "Write tests FIRST, ensure they FAIL")
    - .specify/templates/checklist-template.md ✅ aligned (generic template, no constitution references)
  Follow-up TODOs: None — all placeholders resolved
-->

# Investments Constitution

## Core Principles

### I. Strong Design Patterns

All code MUST follow well-established software design patterns appropriate to the problem domain.

- **Pattern selection**: Choose patterns (e.g., Repository, Strategy, Observer, Factory, Adapter) based on the
  specific problem being solved, not on personal preference or novelty.
- **Separation of concerns**: Each module, class, and function MUST have a single, well-defined responsibility.
  Cross-cutting concerns (logging, authentication, caching) MUST be handled through dedicated infrastructure
  layers, not mixed into business logic.
- **Explicit over implicit**: Behavior MUST be explicit and traceable. Avoid "magic" — no hidden side effects,
  no implicit global state, no framework auto-wiring that obscures control flow.
- **Inversion of Control**: Dependencies MUST be injected, not constructed internally. Every component MUST
  declare its dependencies at its boundary so they can be substituted for testing and evolution.
- **Rationale**: Consistent patterns reduce cognitive load, make the codebase predictable for any contributor,
  and enable safe refactoring. Patterns provide a shared vocabulary that accelerates code review and onboarding.

### II. Test-Driven Development (NON-NEGOTIABLE)

TDD is mandatory for all feature work. No production code may be written without a failing test first.

- **Red-Green-Refactor cycle MUST be followed strictly**:
  1. Write a test that defines the expected behavior (the test MUST fail)
  2. Write the minimum code to make the test pass
  3. Refactor while keeping all tests green
- **Test categories by scope**:
  - **Unit tests**: Cover individual functions and methods in isolation. Dependencies MUST be mocked/stubbed.
  - **Integration tests**: Cover interactions between real components (database, file system, network).
    MUST verify that contracts between modules hold.
  - **Contract tests**: Cover public API boundaries — verify request/response schemas, error codes, and
    backwards compatibility promises.
  - **End-to-end tests**: Cover critical user journeys from entry point to outcome.
- **No untested code lands on the main branch.** Pull requests without corresponding tests MUST be rejected.
- **Test quality standards**: Tests MUST be deterministic (no flaky tests), fast (unit < 10ms, integration
  < 5s per suite where practical), and independent (no test ordering dependencies).
- **Rationale**: TDD ensures every line of code exists for a reason. It catches regressions immediately,
  documents expected behavior, and enables fearless refactoring. It is the single most effective practice
  for maintaining code quality at scale.

### III. User Experience Consistency

Every user-facing feature MUST deliver a consistent, predictable, and accessible experience.

- **Design system compliance**: All UI components MUST use the project's design system for typography,
  spacing, color, and interaction patterns. No one-off styles.
- **Accessibility MUST be built-in, not bolted-on**:
  - All interactive elements MUST be keyboard-navigable
  - All non-text content MUST have text alternatives
  - Color MUST not be the sole means of conveying information
  - Target WCAG 2.1 AA compliance as the minimum bar
- **Error states and loading**: Every user-facing interaction MUST handle four states:
  1. Loading (skeleton/spinner/indicator)
  2. Empty (meaningful empty-state messaging with a call to action)
  3. Error (user-friendly error message with recovery path)
  4. Success (confirmation of completed action)
- **Responsive-first**: Layouts MUST adapt gracefully from mobile to desktop. Use mobile-first breakpoints.
  No feature may be desktop-only unless the platform itself is desktop-only.
- **Consistent language**: UI copy MUST use consistent terminology across all surfaces. The same action
  MUST be described the same way everywhere.
- **Rationale**: Consistency builds user trust and reduces cognitive load. An inconsistent UX leads to
  confusion, increased support burden, and user churn. Accessibility is a fundamental right, not a feature.

### IV. Code Simplicity & Readability

Code is read far more often than it is written. Write for the reader, not the writer.

- **YAGNI (You Ain't Gonna Need It)**: Do not build functionality speculatively. Features MUST be driven
  by validated requirements, not hunches about future needs.
- **Maximum complexity thresholds**:
  - Functions: SHOULD NOT exceed 30 lines. Exceeding this requires an explicit comment justifying why.
  - Files: SHOULD NOT exceed 400 lines. Larger files MUST be split along responsibility boundaries.
  - Cyclomatic complexity: SHOULD stay under 10 per function. Violations trigger mandatory refactoring review.
- **Naming MUST be intention-revealing**: Variable, function, and class names MUST communicate what they
  do without requiring comments. Avoid abbreviations unless they are universally understood in the domain.
- **Comments explain why, not what**: Code should be self-documenting for the "what". Comments are for
  non-obvious rationale, trade-offs, and references to external context (issue trackers, RFCs).
- **Rationale**: Simple code has fewer bugs, is easier to test, and is more maintainable. Complexity is a
  liability that must be continuously managed.

### V. Continuous Integration & Deployment Readiness

The codebase MUST be in a deployable state at all times.

- **Trunk-based development**: Work in short-lived feature branches (ideally < 2 days). Merge to main
  frequently. Long-running branches MUST be explicitly justified.
- **Build MUST never be broken on main.** Fixing a broken build takes priority over all other work.
- **Automated checks on every push**:
  - Linting and formatting (must pass)
  - All tests (must pass)
  - Type checking (must pass, for typed languages)
  - Security vulnerability scan (no HIGH/CRITICAL findings)
- **Immutable deployments**: Deployed artifacts MUST be versioned and never mutated in place. Rollbacks
  MUST be as simple as deploying the previous version.
- **Environment parity**: Development, staging, and production environments MUST be as similar as possible.
  Configuration differences MUST be explicit and documented.
- **Rationale**: Deployment pain is inversely proportional to deployment frequency. If deploying is scary,
  deploy more often, not less. CI/CD discipline removes the human error factor from releases.

## Design & Architecture Constraints

- **Language/Framework choice**: Determined per-feature in the implementation plan based on project
  requirements and team expertise. The decision MUST be documented with rationale and alternatives considered.
- **Data storage**: Schema changes MUST be versioned through migrations. Rollback migrations MUST be
  provided alongside forward migrations. No direct database access from UI layer — all data access MUST
  go through a defined service or repository layer.
- **API design**: Public APIs MUST follow RESTful conventions (or GraphQL where appropriate). All endpoints
  MUST be versioned. Breaking changes require a new API version; the previous version MUST be supported
  during a documented deprecation window.
- **Security by default**: Input validation on all external boundaries. Secrets MUST never be committed to
  version control. Authentication and authorization MUST be applied at the service boundary, not
  conditionally within business logic.

## Development Workflow & Quality Gates

- **Code review is mandatory**: Every change MUST be reviewed by at least one other developer before merge.
  Reviewers MUST verify: correctness, test coverage, design pattern compliance, accessibility, and
  constitution alignment.
- **Definition of Done**: A feature is done when:
  1. All tests pass (unit, integration, contract, E2E as applicable)
  2. Code review is approved
  3. Documentation is updated (API docs, README, runbooks)
  4. Feature flag is removed or enabled (no dead feature flags in codebase)
  5. Monitoring/alerting is in place for critical paths
- **Technical debt**: Any accepted technical debt MUST be tracked as an issue with a clear remediation plan
  and deadline. Accumulated debt over a quarter triggers a mandatory clean-up sprint.

## Governance

This constitution is the highest authority for all development decisions in this project. It supersedes
individual preferences, team conventions, and ad-hoc practices.

- **Amendment process**: Changes to this constitution require:
  1. A written proposal documenting the change, rationale, and impact assessment
  2. Team discussion and consensus (not just majority)
  3. Update of all dependent templates and documentation
  4. Version increment following semantic versioning (MAJOR for principle removal/redefinition, MINOR for
     additions, PATCH for clarifications)
- **Compliance**: All pull requests MUST include a brief constitution compliance statement. Violations
  discovered during review MUST be resolved before merge unless a justified exception is explicitly approved
  and documented.
- **Complexity justification**: Any architectural decision introducing additional complexity (new pattern,
  new dependency, new infrastructure) MUST be justified against the Simplicity principle with a written
  rationale in the implementation plan.

**Version**: 1.0.0 | **Ratified**: 2026-07-10 | **Last Amended**: 2026-07-10

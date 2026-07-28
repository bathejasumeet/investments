"""Generic Monte Carlo projection helpers for portfolio simulations."""

from __future__ import annotations

import csv
import io
import math
import random
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

DEFAULT_PERCENTILES: tuple[float, ...] = (5.0, 10.0, 25.0, 50.0, 75.0, 90.0, 95.0)
DEFAULT_VAR_LEVEL = 5.0


@dataclass(frozen=True)
class MonteCarloSummary:
    """Summary statistics for simulation outcomes."""

    probability_of_success: float
    projected_value_median: float
    projected_value_p10: float
    projected_value_p90: float
    shortfall: float
    percentiles: dict[float, float] = field(default_factory=dict)
    mean: float = 0.0
    std: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    var_5: float = 0.0
    cvar_5: float = 0.0


@dataclass(frozen=True)
class YearlyPercentileBand:
    """Percentile ladder at a year boundary along simulation paths."""

    year: int
    percentiles: dict[float, float]


@dataclass(frozen=True)
class MonteCarloResult:
    """Full Monte Carlo output including terminal values and path bands."""

    summary: MonteCarloSummary
    final_values: list[float]
    yearly_bands: list[YearlyPercentileBand] = field(default_factory=list)
    required_monthly_contribution: float | None = None


@dataclass(frozen=True)
class MonteCarloConfig:
    """Configuration knobs for a Monte Carlo run."""

    current_value: float
    monthly_contribution: float
    years: float
    expected_return: float
    volatility: float
    num_simulations: int = 1000
    target_amount: float = 0.0
    inflation_rate: float = 0.0
    fee_drag: float = 0.0
    contribution_timing: str = "start"  # "start" | "end"
    seed: int | None = None
    percentiles: Sequence[float] = DEFAULT_PERCENTILES
    var_level: float = DEFAULT_VAR_LEVEL
    real_terms: bool = True
    store_yearly_paths: bool = True


def run_monte_carlo_projection(
    *,
    current_value: float,
    monthly_contribution: float,
    years: float,
    expected_return: float,
    volatility: float,
    num_simulations: int,
    rng: random.Random | None = None,
    inflation_rate: float = 0.0,
    fee_drag: float = 0.0,
    contribution_timing: str = "start",
    real_terms: bool = False,
) -> list[float]:
    """Project a portfolio forward using geometric Brownian motion.

    Backward-compatible entry point that returns terminal values only.
    """
    result = run_monte_carlo(
        MonteCarloConfig(
            current_value=current_value,
            monthly_contribution=monthly_contribution,
            years=years,
            expected_return=expected_return,
            volatility=volatility,
            num_simulations=num_simulations,
            inflation_rate=inflation_rate,
            fee_drag=fee_drag,
            contribution_timing=contribution_timing,
            real_terms=real_terms,
            store_yearly_paths=False,
        ),
        rng=rng,
    )
    return result.final_values


def run_monte_carlo(
    config: MonteCarloConfig,
    rng: random.Random | None = None,
) -> MonteCarloResult:
    """Run a full Monte Carlo projection with rich summary and path bands."""
    if rng is None:
        rng = random.Random(config.seed) if config.seed is not None else random.Random()

    months = int(math.ceil(max(0.0, config.years) * 12.0))
    net_return = config.expected_return - config.fee_drag
    monthly_return = net_return / 12.0
    monthly_vol = max(0.0, config.volatility) / math.sqrt(12.0)
    monthly_inflation = config.inflation_rate / 12.0
    timing = (config.contribution_timing or "start").lower()
    if timing not in {"start", "end"}:
        timing = "start"

    final_values: list[float] = []
    year_ends = list(range(12, months + 1, 12)) if config.store_yearly_paths else []
    if config.store_yearly_paths and months > 0 and (not year_ends or year_ends[-1] != months):
        # Always capture the terminal month as a band point.
        year_ends = year_ends  # yearly only; terminal covered by final_values
    path_snapshots: dict[int, list[float]] = {m: [] for m in year_ends}

    contribution = max(0.0, config.monthly_contribution)
    start_value = max(0.0, config.current_value)

    if months <= 0:
        finals = [start_value] * max(0, config.num_simulations)
        summary = summarize_monte_carlo(
            finals,
            target_amount=config.target_amount,
            percentiles=config.percentiles,
            var_level=config.var_level,
        )
        return MonteCarloResult(summary=summary, final_values=finals, yearly_bands=[])

    for _ in range(config.num_simulations):
        value = start_value
        for month in range(1, months + 1):
            if timing == "start":
                value += contribution
            shock = rng.gauss(0.0, 1.0)
            growth = monthly_return + monthly_vol * shock
            value *= 1.0 + growth
            if timing == "end":
                value += contribution
            value = max(0.0, value)
            if config.real_terms and monthly_inflation != 0.0:
                # Keep path in nominal units; deflate only at snapshot/final.
                pass
            if month in path_snapshots:
                snap = value
                if config.real_terms and config.inflation_rate != 0.0:
                    snap = value / ((1.0 + config.inflation_rate) ** (month / 12.0))
                path_snapshots[month].append(snap)
        terminal = value
        if config.real_terms and config.inflation_rate != 0.0:
            terminal = value / ((1.0 + config.inflation_rate) ** (months / 12.0))
        final_values.append(terminal)

    summary = summarize_monte_carlo(
        final_values,
        target_amount=config.target_amount,
        percentiles=config.percentiles,
        var_level=config.var_level,
    )
    bands = _build_yearly_bands(path_snapshots, config.percentiles)
    return MonteCarloResult(summary=summary, final_values=final_values, yearly_bands=bands)


def run_multi_asset_monte_carlo(
    *,
    current_value: float,
    monthly_contribution: float,
    years: float,
    weights: Sequence[float],
    expected_returns: Sequence[float],
    covariance: Sequence[Sequence[float]],
    num_simulations: int = 1000,
    target_amount: float = 0.0,
    inflation_rate: float = 0.0,
    fee_drags: Sequence[float] | None = None,
    contribution_timing: str = "start",
    seed: int | None = None,
    percentiles: Sequence[float] = DEFAULT_PERCENTILES,
    var_level: float = DEFAULT_VAR_LEVEL,
    real_terms: bool = True,
    store_yearly_paths: bool = True,
    rng: random.Random | None = None,
) -> MonteCarloResult:
    """Correlated multi-asset GBM with monthly rebalancing to target weights."""
    n = len(weights)
    if n == 0:
        raise ValueError("weights must not be empty")
    if len(expected_returns) != n:
        raise ValueError("expected_returns length must match weights")
    if len(covariance) != n or any(len(row) != n for row in covariance):
        raise ValueError("covariance must be an n x n matrix")

    if rng is None:
        rng = random.Random(seed) if seed is not None else random.Random()

    w = _normalize_weights(weights)
    fees = list(fee_drags) if fee_drags is not None else [0.0] * n
    if len(fees) != n:
        raise ValueError("fee_drags length must match weights")

    net_mu = [expected_returns[i] - fees[i] for i in range(n)]
    monthly_mu = [m / 12.0 for m in net_mu]
    monthly_cov = [[covariance[i][j] / 12.0 for j in range(n)] for i in range(n)]
    chol = _cholesky(monthly_cov)

    months = int(math.ceil(max(0.0, years) * 12.0))
    timing = (contribution_timing or "start").lower()
    if timing not in {"start", "end"}:
        timing = "start"
    contribution = max(0.0, monthly_contribution)
    start_value = max(0.0, current_value)

    year_ends = list(range(12, months + 1, 12)) if store_yearly_paths else []
    path_snapshots: dict[int, list[float]] = {m: [] for m in year_ends}
    final_values: list[float] = []

    if months <= 0:
        finals = [start_value] * max(0, num_simulations)
        summary = summarize_monte_carlo(
            finals,
            target_amount=target_amount,
            percentiles=percentiles,
            var_level=var_level,
        )
        return MonteCarloResult(summary=summary, final_values=finals, yearly_bands=[])

    for _ in range(num_simulations):
        # Rebalanced each month: hold total value, apply correlated asset returns.
        value = start_value
        for month in range(1, months + 1):
            if timing == "start":
                value += contribution
            z = [rng.gauss(0.0, 1.0) for _ in range(n)]
            shocks = _matvec(chol, z)
            portfolio_growth = 0.0
            for i in range(n):
                asset_growth = monthly_mu[i] + shocks[i]
                portfolio_growth += w[i] * asset_growth
            value *= 1.0 + portfolio_growth
            if timing == "end":
                value += contribution
            value = max(0.0, value)
            if month in path_snapshots:
                snap = value
                if real_terms and inflation_rate != 0.0:
                    snap = value / ((1.0 + inflation_rate) ** (month / 12.0))
                path_snapshots[month].append(snap)
        terminal = value
        if real_terms and inflation_rate != 0.0:
            terminal = value / ((1.0 + inflation_rate) ** (months / 12.0))
        final_values.append(terminal)

    summary = summarize_monte_carlo(
        final_values,
        target_amount=target_amount,
        percentiles=percentiles,
        var_level=var_level,
    )
    bands = _build_yearly_bands(path_snapshots, percentiles)
    return MonteCarloResult(summary=summary, final_values=final_values, yearly_bands=bands)


def summarize_monte_carlo(
    final_values: list[float],
    *,
    target_amount: float,
    percentiles: Sequence[float] = DEFAULT_PERCENTILES,
    var_level: float = DEFAULT_VAR_LEVEL,
) -> MonteCarloSummary:
    """Compute success probability, percentile ladder, and tail-risk stats."""
    if not final_values:
        empty_pct = {float(p): 0.0 for p in percentiles}
        return MonteCarloSummary(
            probability_of_success=0.0,
            projected_value_median=0.0,
            projected_value_p10=0.0,
            projected_value_p90=0.0,
            shortfall=max(0.0, target_amount),
            percentiles=empty_pct,
            mean=0.0,
            std=0.0,
            min_value=0.0,
            max_value=0.0,
            var_5=0.0,
            cvar_5=0.0,
        )

    sorted_values = sorted(final_values)
    successes = sum(1 for v in final_values if v >= target_amount)
    probability = successes / len(final_values)

    pct_map: dict[float, float] = {}
    for p in percentiles:
        pct_map[float(p)] = _percentile(sorted_values, float(p))

    # Ensure classic keys always present for compatibility.
    median = pct_map.get(50.0, _percentile(sorted_values, 50.0))
    p10 = pct_map.get(10.0, _percentile(sorted_values, 10.0))
    p90 = pct_map.get(90.0, _percentile(sorted_values, 90.0))
    pct_map.setdefault(50.0, median)
    pct_map.setdefault(10.0, p10)
    pct_map.setdefault(90.0, p90)

    mean = statistics.fmean(sorted_values)
    std = statistics.pstdev(sorted_values) if len(sorted_values) > 1 else 0.0
    min_value = sorted_values[0]
    max_value = sorted_values[-1]

    var_p = _percentile(sorted_values, var_level)
    tail = [v for v in sorted_values if v <= var_p]
    cvar = statistics.fmean(tail) if tail else var_p

    return MonteCarloSummary(
        probability_of_success=probability,
        projected_value_median=median,
        projected_value_p10=p10,
        projected_value_p90=p90,
        shortfall=target_amount - median,
        percentiles=pct_map,
        mean=mean,
        std=std,
        min_value=min_value,
        max_value=max_value,
        var_5=var_p,
        cvar_5=cvar,
    )


def solve_required_contribution(
    *,
    current_value: float,
    years: float,
    expected_return: float,
    volatility: float,
    target_amount: float,
    target_probability: float = 0.80,
    num_simulations: int = 1000,
    inflation_rate: float = 0.0,
    fee_drag: float = 0.0,
    contribution_timing: str = "start",
    seed: int | None = None,
    real_terms: bool = True,
    max_monthly: float = 50_000.0,
    tolerance: float = 0.01,
    max_iterations: int = 24,
) -> float:
    """Binary-search the monthly contribution that hits a success probability."""
    target_probability = min(1.0, max(0.0, target_probability))
    base_seed = seed if seed is not None else 42

    def _prob(monthly: float) -> float:
        result = run_monte_carlo(
            MonteCarloConfig(
                current_value=current_value,
                monthly_contribution=monthly,
                years=years,
                expected_return=expected_return,
                volatility=volatility,
                num_simulations=num_simulations,
                target_amount=target_amount,
                inflation_rate=inflation_rate,
                fee_drag=fee_drag,
                contribution_timing=contribution_timing,
                seed=base_seed,
                real_terms=real_terms,
                store_yearly_paths=False,
            )
        )
        return result.summary.probability_of_success

    # If already successful with zero contribution.
    if _prob(0.0) >= target_probability:
        return 0.0

    lo = 0.0
    hi = max(1.0, max_monthly)
    if _prob(hi) < target_probability:
        # Could not reach target even at max — return max as best effort.
        return hi

    for _ in range(max_iterations):
        mid = (lo + hi) / 2.0
        if _prob(mid) >= target_probability:
            hi = mid
        else:
            lo = mid
        if hi - lo < tolerance:
            break
    return hi


def estimate_return_and_vol_from_prices(
    closes: Sequence[float],
    *,
    periods_per_year: float = 252.0,
) -> tuple[float, float] | None:
    """Estimate annualized return and volatility from a price series."""
    if len(closes) < 3:
        return None
    returns: list[float] = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        curr = closes[i]
        if prev <= 0 or curr <= 0:
            continue
        returns.append(math.log(curr / prev))
    if len(returns) < 2:
        return None
    mean_r = statistics.fmean(returns)
    std_r = statistics.pstdev(returns)
    annual_return = math.exp(mean_r * periods_per_year) - 1.0
    annual_vol = std_r * math.sqrt(periods_per_year)
    return annual_return, annual_vol


def estimate_portfolio_params(
    asset_closes: dict[str, Sequence[float]],
    weights: dict[str, float],
    *,
    periods_per_year: float = 252.0,
) -> tuple[float, float] | None:
    """Estimate blended portfolio μ and σ from aligned asset price histories.

    Uses log returns, pairwise covariance on overlapping dates (equal-length
    trimmed series), and annualizes. Returns None if insufficient data.
    """
    tickers = [t for t in weights if t in asset_closes and len(asset_closes[t]) >= 3]
    if not tickers:
        return None

    min_len = min(len(asset_closes[t]) for t in tickers)
    if min_len < 3:
        return None

    # Use the most recent min_len points for each series.
    series = {t: list(asset_closes[t])[-min_len:] for t in tickers}
    log_returns: dict[str, list[float]] = {}
    for t in tickers:
        rets: list[float] = []
        closes = series[t]
        for i in range(1, len(closes)):
            if closes[i - 1] <= 0 or closes[i] <= 0:
                rets.append(0.0)
            else:
                rets.append(math.log(closes[i] / closes[i - 1]))
        log_returns[t] = rets

    w = _normalize_weights([weights[t] for t in tickers])
    n = len(tickers)
    means = [statistics.fmean(log_returns[t]) for t in tickers]

    # Covariance matrix of daily log returns.
    cov: list[list[float]] = [[0.0] * n for _ in range(n)]
    t_count = len(log_returns[tickers[0]])
    for i in range(n):
        ri = log_returns[tickers[i]]
        for j in range(n):
            rj = log_returns[tickers[j]]
            cov[i][j] = sum(
                (ri[k] - means[i]) * (rj[k] - means[j]) for k in range(t_count)
            ) / t_count

    port_mean = sum(w[i] * means[i] for i in range(n))
    port_var = 0.0
    for i in range(n):
        for j in range(n):
            port_var += w[i] * w[j] * cov[i][j]

    annual_return = math.exp(port_mean * periods_per_year) - 1.0
    annual_vol = math.sqrt(max(0.0, port_var)) * math.sqrt(periods_per_year)
    return annual_return, annual_vol


def build_covariance_from_prices(
    asset_closes: dict[str, Sequence[float]],
    tickers: Sequence[str],
    *,
    periods_per_year: float = 252.0,
) -> list[list[float]] | None:
    """Build an annualized covariance matrix from price histories."""
    usable = [t for t in tickers if t in asset_closes and len(asset_closes[t]) >= 3]
    if len(usable) != len(tickers):
        return None
    min_len = min(len(asset_closes[t]) for t in usable)
    if min_len < 3:
        return None

    series = {t: list(asset_closes[t])[-min_len:] for t in usable}
    log_returns: list[list[float]] = []
    for t in usable:
        rets: list[float] = []
        closes = series[t]
        for i in range(1, len(closes)):
            if closes[i - 1] <= 0 or closes[i] <= 0:
                rets.append(0.0)
            else:
                rets.append(math.log(closes[i] / closes[i - 1]))
        log_returns.append(rets)

    n = len(usable)
    means = [statistics.fmean(r) for r in log_returns]
    t_count = len(log_returns[0])
    cov = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            daily = sum(
                (log_returns[i][k] - means[i]) * (log_returns[j][k] - means[j])
                for k in range(t_count)
            ) / t_count
            cov[i][j] = daily * periods_per_year
    return cov


def percentiles_to_csv(
    summary: MonteCarloSummary,
    *,
    yearly_bands: Sequence[YearlyPercentileBand] | None = None,
) -> str:
    """Serialize percentile ladder (and optional yearly bands) to CSV text."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["scope", "year", "percentile", "value"])
    for p, value in sorted(summary.percentiles.items()):
        writer.writerow(["terminal", "", f"P{p:g}", f"{value:.6f}"])
    writer.writerow(["terminal", "", "mean", f"{summary.mean:.6f}"])
    writer.writerow(["terminal", "", "std", f"{summary.std:.6f}"])
    writer.writerow(["terminal", "", "min", f"{summary.min_value:.6f}"])
    writer.writerow(["terminal", "", "max", f"{summary.max_value:.6f}"])
    writer.writerow(["terminal", "", "var", f"{summary.var_5:.6f}"])
    writer.writerow(["terminal", "", "cvar", f"{summary.cvar_5:.6f}"])
    writer.writerow(
        ["terminal", "", "probability_of_success", f"{summary.probability_of_success:.6f}"]
    )
    if yearly_bands:
        for band in yearly_bands:
            for p, value in sorted(band.percentiles.items()):
                writer.writerow(["yearly", band.year, f"P{p:g}", f"{value:.6f}"])
    return buf.getvalue()


def _build_yearly_bands(
    path_snapshots: dict[int, list[float]],
    percentiles: Sequence[float],
) -> list[YearlyPercentileBand]:
    bands: list[YearlyPercentileBand] = []
    for month in sorted(path_snapshots):
        values = sorted(path_snapshots[month])
        if not values:
            continue
        pct = {float(p): _percentile(values, float(p)) for p in percentiles}
        bands.append(YearlyPercentileBand(year=month // 12, percentiles=pct))
    return bands


def _percentile(sorted_values: list[float], percentile: float) -> float:
    """Linear-interpolated percentile for ascending values."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (percentile / 100.0) * (len(sorted_values) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return sorted_values[lower]

    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _normalize_weights(weights: Iterable[float]) -> list[float]:
    values = [max(0.0, float(w)) for w in weights]
    total = sum(values)
    if total <= 0:
        n = len(values)
        return [1.0 / n] * n if n else []
    return [v / total for v in values]


def _cholesky(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    """Cholesky decomposition; falls back to diagonal vol if not PSD."""
    n = len(matrix)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                val = matrix[i][i] - s
                if val <= 1e-12:
                    # Not positive definite — use a tiny floor on diagonal.
                    lower[i][j] = math.sqrt(max(matrix[i][i], 1e-12))
                else:
                    lower[i][j] = math.sqrt(val)
            else:
                diag = lower[j][j]
                if abs(diag) < 1e-15:
                    lower[i][j] = 0.0
                else:
                    lower[i][j] = (matrix[i][j] - s) / diag
    return lower


def _matvec(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> list[float]:
    return [sum(row[j] * vector[j] for j in range(len(vector))) for row in matrix]

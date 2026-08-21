"""
engine/metrics.py — return and risk metrics.

Two rules, both non-negotiable (ARCHITECTURE.md §2):
  1. DETERMINISTIC. Same input bytes -> same output numbers, forever.
     A change that moves a golden number is a METHODOLOGY change and needs a
     METHODOLOGY_VERSION bump, never a silent fix.
  2. NEVER reads the database. Everything arrives in the payload. That is what
     makes it replayable years later when a fund manager disputes a rank.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

ENGINE_VERSION = "0.1.0"

WINDOW_DAYS: dict[str, int] = {
    "1m": 30, "3m": 91, "6m": 182, "1y": 365, "3y": 1095, "5y": 1825,
}

# Observations must SPAN at least this fraction of a window before it is
# reported. Without it, two prices a week apart emitted a "3y" metric: coverage
# correctly read 0.013, but the number was still LABELLED a three-year return
# and could reach a page. Caught by the golden tests on their first run.
#
# Set to 0.8, not 0.5, deliberately. At 0.5 a "1-year return" could be printed
# from under seven months of data — annualised correctly, but labelled in a way
# that misleads a retail investor. Raising it costs some coverage on young
# funds, which is the right trade for a product whose proposition is that the
# numbers can be trusted. Those funds show "New — insufficient history" instead.
MIN_WINDOW_SPAN = 0.8


@dataclass(frozen=True)
class Observation:
    as_of: date
    nav: float | None = None
    yield_annualised: float | None = None  # decimal, 0.1875 = 18.75%


def _parse_date(v) -> date:
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def to_observations(raw: Iterable[dict]) -> list[Observation]:
    """Parse, drop unusable points, sort ascending, de-duplicate by date."""
    out: dict[date, Observation] = {}
    for r in raw:
        d = _parse_date(r["as_of"])
        nav = r.get("nav")
        y = r.get("yield_annualised")
        nav = float(nav) if nav not in (None, "") else None
        y = float(y) if y not in (None, "") else None
        if nav is None and y is None:
            continue
        if nav is not None and nav <= 0:
            continue  # a non-positive unit price is a data error, not a value
        out[d] = Observation(as_of=d, nav=nav, yield_annualised=y)
    return [out[k] for k in sorted(out)]


def _median_gap_days(obs: list[Observation]) -> float:
    if len(obs) < 2:
        return 0.0
    gaps = sorted((obs[i].as_of - obs[i - 1].as_of).days for i in range(1, len(obs)))
    mid = len(gaps) // 2
    return float(gaps[mid] if len(gaps) % 2 else (gaps[mid - 1] + gaps[mid]) / 2)


def _periods_per_year(obs: list[Observation]) -> float:
    gap = _median_gap_days(obs)
    if gap <= 0:
        return 0.0
    return 365.0 / gap


def _simple_returns(navs: list[float]) -> list[float]:
    return [navs[i] / navs[i - 1] - 1.0 for i in range(1, len(navs))]


def _stdev(xs: list[float]) -> float:
    """Sample standard deviation. Returns 0.0 for fewer than two points."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    return math.sqrt(var)


def max_drawdown(navs: list[float]) -> float:
    """Largest peak-to-trough fall, as a NEGATIVE decimal. -0.12 = a 12% fall."""
    if len(navs) < 2:
        return 0.0
    peak = navs[0]
    worst = 0.0
    for v in navs:
        if v > peak:
            peak = v
        dd = v / peak - 1.0
        if dd < worst:
            worst = dd
    return worst


def downside_deviation(returns: list[float], periods_per_year: float,
                       target: float = 0.0) -> float:
    """Annualised deviation of returns below target. Zero when none fall below."""
    below = [min(0.0, r - target) for r in returns]
    if not below or all(b == 0.0 for b in below):
        return 0.0
    n = len(below)
    var = sum(b ** 2 for b in below) / n
    return math.sqrt(var) * math.sqrt(periods_per_year) if periods_per_year else 0.0


def annualise(total_return: float, days: int) -> float | None:
    """
    Compound a period return to an annual rate.

    Returns None below 30 days: annualising a one-week move produces a headline
    figure with no informational content and enormous variance. Better to show
    nothing than a number nobody should act on.
    """
    if days < 30 or total_return <= -1.0:
        return None
    return (1.0 + total_return) ** (365.0 / days) - 1.0


def _series_mean(series: list[dict], start: date, end: date) -> float | None:
    """Mean of a benchmark series over a window. Values are decimals."""
    vals = [float(p["value"]) for p in series
            if start <= _parse_date(p["as_of"]) <= end]
    return sum(vals) / len(vals) if vals else None


def compute_window(obs: list[Observation], window_code: str, as_of: date,
                   tbill: list[dict] | None = None,
                   cpi: list[dict] | None = None) -> dict | None:
    """Metrics for one window, or None when the window holds too little data."""
    days = WINDOW_DAYS[window_code]
    start = as_of - timedelta(days=days)
    win = [o for o in obs if start <= o.as_of <= as_of]
    if len(win) < 2:
        return None

    span_days = (win[-1].as_of - win[0].as_of).days
    if span_days < days * MIN_WINDOW_SPAN:
        return None

    expected = max(1.0, days / _median_gap_days(obs)) if _median_gap_days(obs) else 1.0
    coverage = min(1.0, len(win) / expected)
    ppy = _periods_per_year(win)
    actual_days = (win[-1].as_of - win[0].as_of).days or 1

    navs = [o.nav for o in win if o.nav is not None]
    result: dict = {
        "window_code": window_code,
        "observation_count": len(win),
        "span_days": span_days,
        "coverage": round(coverage, 4),
        "engine_version": ENGINE_VERSION,
    }

    if len(navs) >= 2:
        total = navs[-1] / navs[0] - 1.0
        rets = _simple_returns(navs)
        result["total_return"] = total
        result["annualised_return"] = annualise(total, actual_days)
        result["volatility"] = _stdev(rets) * math.sqrt(ppy) if ppy else 0.0
        result["max_drawdown"] = max_drawdown(navs)
        result["downside_deviation"] = downside_deviation(rets, ppy)
        result["positive_period_pct"] = (
            sum(1 for r in rets if r > 0) / len(rets) if rets else None
        )
    else:
        # Yield-quoted products (most Ghanaian money market funds publish a rate,
        # not a unit price). Report the yield; leave price-derived risk metrics
        # absent so the coverage gate excludes those factors rather than
        # inventing them. See scoring-config.ts GATES.COVERAGE_FLOOR.
        ys = [o.yield_annualised for o in win if o.yield_annualised is not None]
        if not ys:
            return None
        result["annualised_return"] = sum(ys) / len(ys)
        result["total_return"] = None
        result["volatility"] = None
        result["max_drawdown"] = None
        result["downside_deviation"] = None
        result["positive_period_pct"] = None

    ann = result.get("annualised_return")
    rf = _series_mean(tbill or [], start, as_of)
    infl = _series_mean(cpi or [], start, as_of)
    result["excess_over_tbill"] = (ann - rf) if (ann is not None and rf is not None) else None
    # Fisher, not subtraction: at 20%+ inflation the approximation is materially wrong.
    result["real_return"] = (
        (1.0 + ann) / (1.0 + infl) - 1.0
        if (ann is not None and infl is not None) else None
    )
    return result


def compute_metrics(payload: dict) -> dict:
    """Entry point. See ARCHITECTURE.md §2 for the request/response contract."""
    obs = to_observations(payload.get("observations", []))
    as_of = _parse_date(payload["as_of"]) if payload.get("as_of") else (
        obs[-1].as_of if obs else date.today()
    )
    benchmarks = payload.get("benchmarks") or {}
    windows = payload.get("windows") or list(WINDOW_DAYS)

    metrics = []
    for w in windows:
        if w not in WINDOW_DAYS:
            continue
        m = compute_window(obs, w, as_of,
                           tbill=benchmarks.get("tbill_91"),
                           cpi=benchmarks.get("cpi_yoy"))
        if m:
            metrics.append(m)

    return {
        "engine_version": ENGINE_VERSION,
        "product_id": payload.get("product_id"),
        "as_of": as_of.isoformat(),
        "observation_count": len(obs),
        "first_observation": obs[0].as_of.isoformat() if obs else None,
        "last_observation": obs[-1].as_of.isoformat() if obs else None,
        "metrics": metrics,
    }

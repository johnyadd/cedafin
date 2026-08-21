r"""
engine/tests/test_metrics.py — golden tests.

Run:  cd engine ; .\.venv\Scripts\Activate.ps1 ; pytest -q

THE RULE (ARCHITECTURE.md §15.3): if a change here moves a number, that is a
METHODOLOGY change. Bump METHODOLOGY_VERSION in lib/scoring/config.ts and add a
CHANGELOG entry. Never "fix" a golden number to make a test pass.
"""

from datetime import date, timedelta

import pytest

from metrics import (annualise, compute_metrics, downside_deviation,
                     max_drawdown, to_observations)

START = date(2025, 8, 1)


def weekly(n, f, key="nav"):
    return [{"as_of": (START + timedelta(days=7 * i)).isoformat(), key: f(i)}
            for i in range(n)]


def flat_series(n, value):
    return [{"as_of": (START + timedelta(days=7 * i)).isoformat(), "value": value}
            for i in range(n)]


# --- primitives -------------------------------------------------------------

def test_max_drawdown_known_value():
    assert max_drawdown([100, 120, 90, 110]) == pytest.approx(-0.25)


def test_max_drawdown_monotonic_rise_is_zero():
    assert max_drawdown([100, 101, 102, 103]) == 0.0


def test_annualise_identity_at_one_year():
    assert annualise(0.10, 365) == pytest.approx(0.10)


def test_annualise_refuses_short_windows():
    """Annualising a one-week move produces a headline with no content."""
    assert annualise(0.02, 7) is None


def test_downside_deviation_zero_when_nothing_below_target():
    assert downside_deviation([0.01, 0.02, 0.03], 52.0) == 0.0


# --- parsing ----------------------------------------------------------------

def test_observations_deduplicate_and_sort():
    raw = [
        {"as_of": "2025-08-08", "nav": 2.0},
        {"as_of": "2025-08-01", "nav": 1.0},
        {"as_of": "2025-08-08", "nav": 2.5},  # later wins
    ]
    obs = to_observations(raw)
    assert [o.as_of.isoformat() for o in obs] == ["2025-08-01", "2025-08-08"]
    assert obs[-1].nav == 2.5


def test_non_positive_nav_is_dropped_as_a_data_error():
    assert to_observations([{"as_of": "2025-08-01", "nav": 0}]) == []


# --- full computation -------------------------------------------------------

def test_smooth_growth_series():
    obs = weekly(60, lambda i: round(100 * (1.002 ** i), 6))
    out = compute_metrics({
        "product_id": "smooth", "as_of": obs[-1]["as_of"], "observations": obs,
        "benchmarks": {"tbill_91": flat_series(60, 0.18),
                       "cpi_yoy": flat_series(60, 0.20)},
        "windows": ["1y"],
    })
    m = out["metrics"][0]
    assert m["annualised_return"] == pytest.approx(0.1098, abs=1e-3)
    assert m["volatility"] < 1e-4          # residual is NAV rounding at 6dp
    assert m["max_drawdown"] == 0.0
    assert m["excess_over_tbill"] < 0      # 11% nominal against an 18% T-bill
    assert m["real_return"] < 0            # and against 20% inflation


def test_real_return_uses_fisher_not_subtraction():
    """
    At Ghanaian inflation levels the approximation is materially wrong.
    18.75% nominal against 20% inflation is -1.04% real, not -1.25%.
    """
    obs = weekly(60, lambda i: 0.1875, key="yield_annualised")
    out = compute_metrics({
        "product_id": "mmf", "as_of": obs[-1]["as_of"], "observations": obs,
        "benchmarks": {"cpi_yoy": flat_series(60, 0.20)}, "windows": ["1y"],
    })
    assert out["metrics"][0]["real_return"] == pytest.approx(-0.010417, abs=1e-6)


def test_yield_quoted_fund_omits_price_derived_risk_metrics():
    """
    Most Ghanaian money market funds publish a rate, not a unit price. Report
    the yield; leave volatility and drawdown ABSENT so the coverage gate drops
    those factors rather than the engine inventing them.
    """
    obs = weekly(60, lambda i: 0.1875, key="yield_annualised")
    m = compute_metrics({"product_id": "mmf", "as_of": obs[-1]["as_of"],
                         "observations": obs, "windows": ["1y"]})["metrics"][0]
    assert m["annualised_return"] == pytest.approx(0.1875)
    assert m["volatility"] is None
    assert m["max_drawdown"] is None


def test_window_not_spanned_by_the_data_is_omitted_not_guessed():
    """
    Regression, found by this test on its first run. Two prices a week apart
    used to emit a "3y" metric: coverage correctly read 0.013, but the number
    was still labelled a three-year return and could have reached a page.
    A window is now reported only when the observations span at least half of
    it (MIN_WINDOW_SPAN).
    """
    # 30 weeks = 203 days: clears 6m (needs 146), short of 1y (needs 292).
    obs = weekly(30, lambda i: round(100 * (1.001 ** i), 6))
    out = compute_metrics({"product_id": "sparse", "as_of": obs[-1]["as_of"],
                           "observations": obs,
                           "windows": ["1m", "3m", "6m", "1y", "3y"]})
    reported = [m["window_code"] for m in out["metrics"]]
    assert "6m" in reported
    assert "1y" not in reported and "3y" not in reported


def test_two_points_a_week_apart_report_nothing_at_all():
    obs = weekly(2, lambda i: 100 + i)
    out = compute_metrics({"product_id": "sparse", "as_of": obs[-1]["as_of"],
                           "observations": obs, "windows": ["1m", "1y", "3y"]})
    assert out["metrics"] == []


def test_determinism():
    """Same input twice, same output. The whole engine contract in one test."""
    obs = weekly(40, lambda i: round(100 * (1.001 ** i), 6))
    payload = {"product_id": "d", "as_of": obs[-1]["as_of"], "observations": obs,
               "windows": ["3m", "6m"]}
    assert compute_metrics(dict(payload)) == compute_metrics(dict(payload))

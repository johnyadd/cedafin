"""
compute_metrics.py — observations out of Supabase, through the engine, back in.

THE MISSING LINK. There are 120 NAV observations in the database and a tested
metrics engine, and nothing has ever connected them: product_metrics is empty,
so the site compares costs and says nothing about returns.

WHAT IT DOES
For each published product: pull its observation series, post it to the engine,
write the returned metrics to product_metrics. The engine stays stateless — it
reads nothing from the database and everything from the payload, which is what
makes any published figure replayable years later.

TWO THINGS IT DELIBERATELY DOES NOT DO

  REAL RETURNS. metrics.py computes them when a CPI series is supplied, and it
  averages CPI across each return window rather than taking a spot value —
  correct, because Ghanaian inflation went from 23% to 3.2% to 5.3% inside two
  years and the wrong month materially changes the answer. Only two CPI points
  are loaded, both mid-2026, so a trailing 12-month return would be measured
  against inflation from outside its own window. That would overstate real
  returns, on the one figure the site's credibility rests on. So CPI is passed
  only when the series actually covers the window, and real_return comes back
  null otherwise.

  CHAINED-SERIES PRICES. A chained level is an index built from published
  monthly returns, base 100. Volatility, drawdown and return are all valid on
  it because they depend on relative movement — its LEVEL is not a dealing
  price. That distinction lives in nav_observations.series_kind and is carried
  through here.

Usage:
    python compute_metrics.py --dry-run
    python compute_metrics.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date


def env() -> dict:
    """
    Credentials from .env.local locally, from the environment in CI.

    A scheduled run has no .env.local — the file holds a service-role key and
    the repository is public. It has environment variables instead, supplied
    from repository secrets.
    """
    out = {}
    if os.path.exists(".env.local"):
        for line in open(".env.local", encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()

    # Environment wins, so a scheduled run is never affected by a stale file.
    for k in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if os.environ.get(k):
            out[k] = os.environ[k]

    missing = [k for k in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") if not out.get(k)]
    if missing:
        print(f"Missing {chr(44).join(missing)} — not in .env.local or the environment.")
        sys.exit(1)
    return out


E = env()
BASE = E["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = E["SUPABASE_SERVICE_ROLE_KEY"]
ENGINE = E.get("PYTHON_ENGINE_URL", "http://localhost:8000").rstrip("/")
HDRS = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json", "Prefer": "return=representation"}

WINDOWS = ["1m", "3m", "6m", "1y", "3y", "5y"]


def rest(method: str, path: str, body=None, prefer: str | None = None) -> list:
    h = dict(HDRS)
    if prefer:
        h["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}\n  "
                           f"{e.read().decode('utf-8', 'replace')[:300]}") from e


# The maths, imported rather than called over HTTP.
#
# This used to POST to a FastAPI service on localhost:8000. That service was
# never deployed anywhere — Render has one engine and it belongs to another
# project — so every scheduled run failed, and continue-on-error made the job
# go green anyway. The metrics on the live site were as old as the last time
# somebody ran this by hand.
#
# Nothing in the Next.js app calls the engine: PYTHON_ENGINE_URL appears only
# in env.ts, in a schema and an unused health check. So the HTTP layer had one
# client, on the same machine, running weekly. engine/main.py stays in the
# repo for the day the site needs live computation; this script does not need
# a web server to add up numbers.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine"))
from metrics import ENGINE_VERSION, compute_metrics as _compute  # noqa: E402


def compute(payload: dict) -> dict | None:
    try:
        return _compute(payload)
    except (KeyError, ValueError) as e:
        # The engine raises these for bad data, which means the ingestion
        # layer let something through. Worth naming the product rather than
        # failing the whole run.
        print(f"    invalid payload: {e}")
        return None


def series(code: str) -> list[dict]:
    rows = rest("GET", f"/macro_series?series_code=eq.{code}"
                       f"&select=as_of,value&order=as_of")
    return [{"as_of": r["as_of"], "value": r["value"]} for r in rows]


def covers(points: list[dict], start: str, end: str) -> bool:
    """
    A benchmark may only be passed if it actually spans the return window.
    Averaging two mid-2026 CPI readings across a window running from early 2025
    would silently produce a wrong real return — the one number this site
    cannot afford to get wrong.
    """
    if not points:
        return False
    have = [p["as_of"] for p in points]
    return min(have) <= start and max(have) >= end


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # No health probe: the engine is imported, so if it were missing this
    # script would not have started.
    version = ENGINE_VERSION
    print(f"Engine {version}, imported\n")

    tbill = series("GH_TBILL_91")
    cpi = series("GH_CPI_YOY")
    print(f"benchmarks: {len(tbill)} T-bill points, {len(cpi)} CPI points")
    if cpi:
        print(f"            CPI covers {min(p['as_of'] for p in cpi)} to "
              f"{max(p['as_of'] for p in cpi)}")
    print()

    products = rest("GET", "/products?status=eq.published"
                           "&select=id,name,share_class,slug&order=name")
    total_rows = skipped_real = 0

    for p in products:
        obs = rest("GET", f"/nav_observations?product_id=eq.{p['id']}"
                          f"&superseded_by=is.null"
                          f"&select=as_of,nav,series_kind&order=as_of")
        if len(obs) < 2:
            print(f"  {p['name'][:36]:<38} {p['share_class']:<5} "
                  f"{len(obs)} points — skipped")
            continue

        start, end = obs[0]["as_of"], obs[-1]["as_of"]
        kind = obs[-1].get("series_kind", "quoted")

        # Both benchmarks are passed always. The engine decides per WINDOW
        # whether each spans the period being measured — see _spans in
        # engine/metrics.py.
        #
        # This used to withhold the CPI unless it covered a product's whole
        # observation history, so an equity priced back to early 2025 got no
        # real return even for its one-year window, which the CPI covers
        # completely. Forty-eight products were affected.
        benchmarks: dict = {"tbill_91": tbill, "cpi_yoy": cpi}
        if not covers(cpi, start, end):
            skipped_real += 1

        out = compute({
            "product_id": p["id"], "as_of": end, "currency": "GHS",
            "observations": [{"as_of": o["as_of"], "nav": o["nav"]} for o in obs],
            "benchmarks": benchmarks, "windows": WINDOWS,
        })
        if not out:
            continue

        metrics = out.get("metrics", [])
        best = next((m for m in metrics if m["window_code"] == "1y"),
                    metrics[-1] if metrics else None)
        label = ""
        if best:
            ann = best.get("annualised_return")
            real = best.get("real_return")
            label = (f"{best['window_code']} "
                     f"{ann * 100:6.2f}%" if ann is not None else "n/a")
            if real is not None:
                label += f"  real {real * 100:5.2f}%"
        print(f"  {p['name'][:36]:<38} {p['share_class']:<5} "
              f"{len(obs):>3} pts  {kind:<8} {len(metrics)} windows  {label}")

        if args.dry_run:
            continue

        rows = [{
            "product_id": p["id"], "as_of": end,
            "window_code": m["window_code"],
            "total_return": m.get("total_return"),
            "annualised_return": m.get("annualised_return"),
            "volatility": m.get("volatility"),
            "max_drawdown": m.get("max_drawdown"),
            "downside_deviation": m.get("downside_deviation"),
            "excess_over_tbill": m.get("excess_over_tbill"),
            "real_return": m.get("real_return"),
            "positive_period_pct": m.get("positive_period_pct"),
            "observation_count": m.get("observation_count", 0),
            "coverage": m.get("coverage", 0),
            "engine_version": out.get("engine_version", version),
        } for m in metrics]
        if rows:
            rest("POST", "/product_metrics", rows,
                 prefer="return=minimal,resolution=merge-duplicates")
            total_rows += len(rows)

    if args.dry_run:
        print("\nDry run — nothing written.")
    else:
        print(f"\n  {total_rows} metric rows written")
    if skipped_real:
        print(f"\n  {skipped_real} product(s) have observations predating the CPI")
        print("  series, so their longest windows carry no real return. The")
        print("  shorter windows do. More monthly CPI from GSS would extend it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

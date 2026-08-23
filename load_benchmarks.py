"""
load_benchmarks.py — T-bill, inflation and FX series into macro_series.

WHY THIS IS HAND-FED RATHER THAN SCRAPED
Bank of Ghana's robots.txt disallows automated access. An earlier fetcher
enumerated their auction PDFs and worked — but it used plain urllib, which
never consults robots.txt, so it took a file the site had asked crawlers not
to. Nobody would have noticed one PDF. It is still the same line we declined
to cross with the paywalled ARG documents, and a site whose whole pitch is
"we cite our sources and respect what providers publish" cannot quietly ignore
a central bank's crawl directive to get its own benchmark data.

It also is not necessary. T-bill rates are one number a week and CPI one a
month — about 64 figures a year. A person reading a public page and recording
the number is entirely legitimate, and that is what sources.kind =
'manual_entry' exists for.

WHY THE BENCHMARKS MATTER
Without GH_TBILL_91 there is no risk-adjusted return; without GH_CPI_YOY there
is no real return, which is the figure no Ghanaian site publishes. And the rate
environment has moved so violently that trailing returns are misleading without
it: the 91-day bill paid 23-25% in February 2025 and 5.63% in August 2026. A
fund's 14% last year and a fund's 14% next year are not the same claim.

Fisher, not subtraction — at Ghanaian inflation levels the approximation is
materially wrong, and metrics.py already computes it correctly. This only has
to load the inputs honestly.

INPUT FORMAT — benchmarks.csv, one row per observation:

    series,as_of,value,source_note
    GH_TBILL_91,2026-08-07,5.6289,BoG tender 2019
    GH_CPI_YOY,2026-07-31,4.6,GSS CPI release July 2026
    GHS_USD,2026-08-07,12.40,BoG interbank

`value` is a PERCENT for rates (5.6289 means 5.6289%) and a RATE for FX.
The loader converts rates to decimals; the schema stores decimals.

Usage:
    python load_benchmarks.py --template     # write a starter benchmarks.csv
    python load_benchmarks.py --dry-run
    python load_benchmarks.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

SERIES = {
    "GH_TBILL_91": ("Bank of Ghana", "91-day Treasury bill", True),
    "GH_TBILL_182": ("Bank of Ghana", "182-day Treasury bill", True),
    "GH_TBILL_364": ("Bank of Ghana", "364-day Treasury bill", True),
    "GH_CPI_YOY": ("Ghana Statistical Service", "Consumer price inflation, year on year", True),
    "GH_POLICY_RATE": ("Bank of Ghana", "Monetary policy rate", True),
    "GHS_USD": ("Bank of Ghana", "Cedi per US dollar, interbank", False),
    "GHS_GBP": ("Bank of Ghana", "Cedi per pound sterling, interbank", False),
    "GSE_CI": ("Ghana Stock Exchange", "GSE Composite Index", False),
}

TEMPLATE = """series,as_of,value,source_note
# One row per observation. Lines starting with # are ignored.
#
# value is a PERCENT for rate series (5.6289 = 5.6289%) and a LEVEL for
# GHS_USD, GHS_GBP and GSE_CI. Do not mix the two.
#
# as_of is the date the figure REFERS to, not the day you typed it.
#
# Where to read them:
#   GH_TBILL_*    bog.gov.gh -> Markets -> Weekly GOG T-Bill Auction Results
#   GH_CPI_YOY    statsghana.gov.gh -> CPI monthly release
#   GHS_USD       bog.gov.gh -> Daily Interbank FX Rates
#
# Verified figures to start from — replace and extend:
GH_TBILL_91,2026-08-07,5.6289,BoG tender 2019
GH_TBILL_182,2026-08-07,7.5265,BoG tender 2019
GH_TBILL_364,2026-08-07,12.9864,BoG tender 2019
GH_CPI_YOY,2026-07-31,4.6,GSS CPI release July 2026
GH_CPI_YOY,2026-06-30,5.3,GSS CPI release June 2026
GH_POLICY_RATE,2026-07-31,14.0,BoG MPC July 2026
"""


def env() -> dict:
    if not os.path.exists(".env.local"):
        print("No .env.local — run from the project root.")
        sys.exit(1)
    out = {}
    for line in open(".env.local", encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


E = env()
BASE = E["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = E["SUPABASE_SERVICE_ROLE_KEY"]
HDRS = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json", "Prefer": "return=representation"}


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="benchmarks.csv")
    ap.add_argument("--template", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.template:
        if os.path.exists(args.file):
            print(f"{args.file} already exists — not overwriting.")
            return 1
        with open(args.file, "w", encoding="utf-8") as f:
            f.write(TEMPLATE)
        print(f"Wrote {args.file}. Fill it in, then run without --template.")
        return 0

    if not os.path.exists(args.file):
        print(f"{args.file} not found. Run with --template to create one.")
        return 1

    rows, problems = [], []
    with open(args.file, encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(
                line for line in f if not line.lstrip().startswith("#")), start=2):
            series = (r.get("series") or "").strip()
            as_of = (r.get("as_of") or "").strip()
            raw = (r.get("value") or "").strip()
            note = (r.get("source_note") or "").strip()

            if series not in SERIES:
                problems.append(f"line {i}: unknown series {series!r}")
                continue
            try:
                date.fromisoformat(as_of)
            except ValueError:
                problems.append(f"line {i}: bad date {as_of!r}")
                continue
            try:
                value = float(raw)
            except ValueError:
                problems.append(f"line {i}: bad value {raw!r}")
                continue

            publisher, label, is_rate = SERIES[series]
            # Rates are stored as DECIMALS, matching product_fees and metrics.
            stored = round(value / 100.0, 8) if is_rate else value

            # A rate above 100% or below zero is a typo, not a market event.
            if is_rate and not (0 <= value <= 100):
                problems.append(f"line {i}: {series} = {value}% is out of range")
                continue

            rows.append({"series": series, "as_of": as_of, "stored": stored,
                         "shown": value, "is_rate": is_rate,
                         "publisher": publisher, "label": label, "note": note})

    if problems:
        print("Problems — nothing loaded:")
        for p in problems:
            print(f"  {p}")
        return 1
    if not rows:
        print(f"No usable rows in {args.file}")
        return 1

    by_series: dict[str, list] = {}
    for r in rows:
        by_series.setdefault(r["series"], []).append(r)

    print(f"{len(rows)} observations across {len(by_series)} series\n")
    for s, rs in sorted(by_series.items()):
        rs.sort(key=lambda x: x["as_of"])
        unit = "%" if rs[0]["is_rate"] else ""
        print(f"  {s:<16} {len(rs):>3} points  "
              f"{rs[0]['as_of']} to {rs[-1]['as_of']}  "
              f"latest {rs[-1]['shown']}{unit}")

    if args.dry_run:
        print("\nDry run — nothing written.")
        return 0

    # One source row per distinct note, so every figure traces to where it was
    # read from and when it was entered.
    src_ids: dict[str, str] = {}
    for note in sorted({r["note"] for r in rows}):
        title = note or "Benchmark entered by hand"
        found = rest("GET", f"/sources?title=eq.{urllib.parse.quote(title)}"
                            f"&kind=eq.manual_entry&select=id")
        if found:
            src_ids[note] = found[0]["id"]
            continue
        publisher = next((r["publisher"] for r in rows if r["note"] == note),
                         "Manual entry")
        src_ids[note] = rest("POST", "/sources", {
            "kind": "manual_entry", "publisher": publisher, "title": title,
        })[0]["id"]

    body = [{
        "series_code": r["series"], "as_of": r["as_of"],
        "value": r["stored"], "source_id": src_ids[r["note"]],
    } for r in rows]

    written = 0
    for i in range(0, len(body), 100):
        rest("POST", "/macro_series", body[i : i + 100],
             prefer="return=minimal,resolution=merge-duplicates")
        written += len(body[i : i + 100])

    print(f"\n  {written} observations loaded into macro_series")
    print("  Rates stored as decimals. Real returns can now be computed —")
    print("  metrics.py averages CPI across each return window and uses the")
    print("  Fisher relation, not subtraction.")
    return 0


if __name__ == "__main__":
    import urllib.parse  # noqa: E402  (used only in the load path)
    sys.exit(main())

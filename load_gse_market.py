"""
load_gse_market.py — index, capitalisation and turnover into macro_series.

WHY macro_series AND NOT A NEW TABLE
These are observations about the market, not about any product: the GSE
Composite Index, total capitalisation, and how much actually changed hands.
macro_series already holds Treasury bill rates, CPI and the policy rate —
every market-wide series the site tracks. The exchange's figures belong
alongside them rather than in a table of their own.

THE TWO SERIES THAT MATTER TOGETHER
    GSE_COMPOSITE_INDEX     what prices did
    GSE_VOLUME_TRADED       how many shares changed hands

Between February 2025 and July 2026 the index rose 172.7% and volume rose
331.2%. Both climbing is the healthy version: prices up because more people are
buying, not because fewer are selling into a thin market.

That correction matters. The July 2026 report shows volume down 71.98% year on
year, and reading only that figure — as this loader's first draft did — makes
the rise look like a liquidity mirage. It is a single month measured against an
exceptional July 2025. Fifteen months of data say the opposite, and a series
beats a snapshot every time.

Charted together the two lines make that obvious. As percentages in prose, a
reader keeps one and drops the other.

WHAT IS DELIBERATELY NOT STORED
The year-on-year change printed beside each figure in the report. A series
computes its own comparisons; a stored percentage goes stale the moment
another month is added, and then two numbers in the same database disagree.

Usage:
    python load_gse_market.py --dry-run
    python load_gse_market.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# CSV column -> macro_series code. Only what a page would actually use.
SERIES = {
    "gse_composite_index": ("GSE_COMPOSITE_INDEX", "GSE Composite Index"),
    "gse_financial_index": ("GSE_FINANCIAL_INDEX", "GSE Financial Stock Index"),
    "gse_market_cap_ghs_mil": ("GSE_MARKET_CAP", "Market capitalisation, GH¢ million"),
    "gse_volume_traded": ("GSE_VOLUME_TRADED", "Shares traded in the month"),
    "gse_value_traded_ghs": ("GSE_VALUE_TRADED", "Value traded in the month, GH¢"),
}


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


def f(v) -> float | None:
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="gse_market.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"{args.csv} not found — run extract_gse.py first.")
        return 1
    rows = sorted(
        csv.DictReader(open(args.csv, encoding="utf-8")),
        key=lambda r: r["as_of"],
    )
    if not rows:
        print("No rows.")
        return 1

    print(f"{len(rows)} month(s), {rows[0]['as_of']} to {rows[-1]['as_of']}\n")

    # Every macro observation must cite where it came from — the table
    # requires it, which is the same rule every figure on this site follows.
    title = "GSE monthly equities market reports"
    src = rest("GET", "/sources?title=eq."
               + urllib.parse.quote(title) + "&select=id")
    source_id = src[0]["id"] if src else rest("POST", "/sources", {
        "kind": "regulator_publication",
        "publisher": "Ghana Stock Exchange",
        "title": title,
    })[0]["id"]

    obs = []
    for col, (code, label) in SERIES.items():
        vals = [(r["as_of"], f(r.get(col))) for r in rows]
        vals = [(d, v) for d, v in vals if v is not None]
        if not vals:
            print(f"  {code:<22} nothing extracted")
            continue
        first, last = vals[0][1], vals[-1][1]
        change = (last / first - 1) * 100 if first else 0
        print(f"  {code:<22} {first:>16,.2f} -> {last:>16,.2f}  "
              f"{change:>+7.1f}%")
        for d, v in vals:
            obs.append({"series_code": code, "as_of": d, "value": v, "source_id": source_id})

    idx = [f(r.get("gse_composite_index")) for r in rows]
    vol = [f(r.get("gse_volume_traded")) for r in rows]
    idx = [v for v in idx if v is not None]
    vol = [v for v in vol if v is not None]
    if len(idx) >= 2 and len(vol) >= 2:
        pmove = ((idx[-1] / idx[0]) - 1) * 100
        vmove = ((vol[-1] / vol[0]) - 1) * 100
        print(f"\n  Prices {pmove:+.1f}%, volume {vmove:+.1f}%.")
        if pmove > 0 and vmove > 0:
            print("  Both rising: prices up because more people are buying,")
            print("  not because fewer are selling into a thin market. The")
            print("  July report's year-on-year volume figure points the")
            print("  other way — that is one month against an exceptional")
            print("  July 2025, and fifteen months say otherwise.")
        elif pmove > 0 and vmove < 0:
            print("  Prices up on falling volume. A quoted price in a market")
            print("  growing quieter is what the last trade happened at, not")
            print("  necessarily what the next one will.")

    if args.dry_run:
        print(f"\nWould write {len(obs)} observation(s) to macro_series.")
        print("Dry run — nothing written.")
        return 0

    codes = ",".join(c for c, _ in SERIES.values())
    rest("DELETE", f"/macro_series?series_code=in.({codes})", prefer="return=minimal")
    for i in range(0, len(obs), 100):
        rest("POST", "/macro_series", obs[i : i + 100], prefer="return=minimal")

    print(f"\n  {len(obs)} observation(s) written to macro_series")
    print("  Alongside the Treasury bill rates and CPI already there — every")
    print("  market-wide series in one place, none of them tied to a product.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

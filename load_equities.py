"""
load_equities.py — the 39 listed shares, with their price history.

WHY THESE ARE NOT ON THE COMPARISON PAGES
A single Ghanaian share and a money market fund are not the same kind of thing,
and ranking them side by side on cost would mislead badly. Shares carry no
management charge, so a cost comparison would place every one of them "cheapest"
above a fund at 1.75% — while the actual cost of owning one is brokerage that
no Ghanaian firm publishes, and the actual risk is a single company.

So equities load with asset_class 'equity' and get their own page. Prices,
market capitalisation and P/E, charted over the period held. Not comparability
that the data cannot support.

WHAT THE PRICE SERIES IS, AND WHAT IT IS NOT
Fifteen monthly closing VWAPs per ticker. The change across them is a PRICE
return, not a total return: dividends are excluded, because the GSE monthly
report does not publish them. Its glossary defines dividend yield — the
dividend paid per share divided by the share price — and then prints the figure
for no company.

That means every return here UNDERSTATES what a holder actually received. Said
plainly on the page, because a number that is wrong in a knowable direction
should say which direction.

THE NUMBER THAT MATTERS MOST IS NOT A PRICE
The GSE Composite Index rose 75.99% in the year to July 2026. Volume traded
fell 71.98% and value traded fell 60% over the same period.

Set against everything else this site tracks — Stanbic Income Fund at 38.80%,
Treasury bills at 5.08%, the Ghana Gold Coin down 3.93% in cedis — Ghanaian
equities beat the lot. On barely any trading. A saver reading the first figure
without the second would draw exactly the wrong conclusion, so the page leads
with both.

Usage:
    python load_equities.py --dry-run
    python load_equities.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SKIP = {"TOTALS", "TOTAL", "GSE", "GSECI", "GSEFSI", "GLD"}

SECTOR_LABEL = {
    "Food And Beverage": "Food and beverage",
    "Ict": "Technology",
    "Mining": "Mining",
    "Banking": "Banking",
    "Insurance": "Insurance",
    "Manufacturing": "Manufacturing",
    "Agriculture": "Agriculture",
    "Oil And Gas": "Oil and gas",
    "Distribution": "Distribution",
    "Education": "Education",
}

ELIGIBILITY = (
    "Bought through a licensed dealing member of the Ghana Stock Exchange. "
    "Brokerage is charged on top and no Ghanaian broker publishes its rates. "
    "A single company carries risk a diversified fund does not."
)


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
    ap.add_argument("--csv", default="gse_equities.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"{args.csv} not found — run extract_gse.py first.")
        return 1
    rows = list(csv.DictReader(open(args.csv, encoding="utf-8")))
    if not rows:
        print("No rows.")
        return 1

    by_ticker: dict[str, list[dict]] = {}
    for r in rows:
        t = r["ticker"]
        if t in SKIP or f(r["closing_vwap"]) is None:
            continue
        by_ticker.setdefault(t, []).append(r)
    for v in by_ticker.values():
        v.sort(key=lambda x: x["as_of"])

    print(f"{len(by_ticker)} ticker(s) with prices\n")

    moves = []
    for t, rs in by_ticker.items():
        if len(rs) < 2:
            continue
        a, b = f(rs[0]["closing_vwap"]), f(rs[-1]["closing_vwap"])
        if a and b:
            moves.append((t, (b / a - 1) * 100, rs[0]["as_of"], rs[-1]["as_of"],
                          len(rs)))
    moves.sort(key=lambda m: -m[1])

    print("  Biggest price moves over the period held:")
    for t, pct, a, b, n in moves[:5]:
        print(f"    {t:<8} {pct:>+8.1f}%   {a} to {b}  ({n} months)")
    if len(moves) > 5:
        print("    ...")
        for t, pct, a, b, n in moves[-3:]:
            print(f"    {t:<8} {pct:>+8.1f}%   {a} to {b}  ({n} months)")

    print("\n  These are PRICE moves. Dividends are excluded because the GSE")
    print("  monthly report does not publish them — its glossary defines")
    print("  dividend yield and prints it for no company. Every figure above")
    print("  therefore understates what a holder actually received.")

    if args.dry_run:
        print(f"\nWould create {len(by_ticker)} equity product(s).")
        print("Dry run — nothing written.")
        return 0

    gse = rest("GET", "/providers?slug=eq.ghana-stock-exchange&select=id")
    if not gse:
        print("Ghana Stock Exchange provider missing — run load_gse.py first.")
        return 1
    provider_id = gse[0]["id"]

    title = "GSE monthly equities market reports"
    src = rest("GET", "/sources?title=eq." + urllib.parse.quote(title) + "&select=id")
    source_id = src[0]["id"] if src else rest("POST", "/sources", {
        "kind": "regulator_publication",
        "publisher": "Ghana Stock Exchange",
        "title": title,
    })[0]["id"]

    have = {p["slug"] for p in rest("GET", "/products?select=slug")}
    made = 0

    for ticker, rs in sorted(by_ticker.items()):
        slug = f"gse-{ticker.lower()}"
        if slug in have:
            continue
        last = rs[-1]
        sector = SECTOR_LABEL.get(last["sector"], last["sector"] or "Listed")

        pid = rest("POST", "/products", {
            "slug": slug,
            "provider_id": provider_id,
            "name": f"{ticker} · {sector}",
            "share_class": "main",
            "market_side": "invest",
            "legal_structure": "other",
            "asset_class": "equity",
            "currency": "GHS",
            # A share may or may not pay a dividend and the report does not
            # say, so this is left false rather than asserted either way.
            "distributes": False,
            "dealing_frequency": "daily",
            "lock_in_days": 0,
            "min_initial_minor": int(round((f(last["closing_vwap"]) or 0) * 100)),
            "min_verified_on": last["as_of"],
            "eligibility_notes": ELIGIBILITY,
            "status": "published",
        })[0]["id"]
        made += 1

        obs = [{
            "product_id": pid,
            "as_of": r["as_of"],
            "nav": f(r["closing_vwap"]),
            "basis": "single",
            "series_kind": "quoted",
            "source_id": source_id,
        } for r in rs if f(r["closing_vwap"]) is not None]
        for i in range(0, len(obs), 100):
            rest("POST", "/nav_observations", obs[i : i + 100],
                 prefer="return=minimal")

    print(f"\n  {made} equity product(s) created")
    print("\n  The index rose 75.99% in the year to July 2026 while volume")
    print("  fell 71.98%. Against Stanbic Income Fund at 38.80%, Treasury")
    print("  bills at 5.08% and the gold coin down 3.93% in cedis, equities")
    print("  beat everything this site tracks — on almost no trading. Both")
    print("  facts belong together or neither is honest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

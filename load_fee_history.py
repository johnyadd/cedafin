"""
load_fee_history.py — build effective-dated fee timelines from every factsheet.

WHY THE FIRST LOADER GOT THIS WRONG
It took ONE fee row per product-class, from that class's latest factsheet. Two
consequences, both real:

  DRIFT   Stanbic Cash Trust main showed 2.00% and its AMC sub-class 2.25% —
          not because the classes charge differently, but because the main
          class had rows through July 2026 and the sub only to February. Same
          fund, two numbers, and both entirely plausible on a page.

  LOSS    25 months of fee history in those PDFs, reduced to one row. Stanbic
          cut the Cash Trust management fee from 2.25% to 2.00% between April
          and June 2026 — an 11% reduction in the cost of holding the fund,
          dated and sourced, thrown away by the loader.

TWO CORRECTIONS

1. FEES ARE FUND-LEVEL. Collect fee observations across ALL classes of a fund,
   build one timeline, apply it to every class. Correct for Stanbic, harmless
   for single-class funds. If a provider ever does charge per class, that needs
   evidence in the document, not an artefact of which class had fresher data.

2. THE TER IS YEAR-TO-DATE, AND THAT MAKES THE DECEMBER FIGURE USEFUL.
   The factsheets label it "(YTD Jun-25)" and the value climbs through each
   year. Publishing a June figure as an annual cost understates it by half. But
   the DECEMBER value is the full year — a real, comparable annual expense
   ratio. So: December becomes the annual TER for that year; the current
   part-year figure is stored separately and labelled as incomplete.

   Stanbic Cash Trust: 2.05% for 2024, 1.86% for 2025. Those are comparable
   numbers no Ghanaian site publishes.

Idempotent: clears existing fee rows for the products it touches, then rebuilds.

Usage:
    python load_fee_history.py --dry-run
    python load_fee_history.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

# Filename stem -> the FUND. Deliberately not per class: the whole point.
FUND_OF = {
    "PDIF_Fact_Sheet": "Platinum Debt Income Fund PLC",
    "Stanbic_Cash_Trust_Fact_Sheet": "Stanbic Cash Trust",
    "Stanbic_Income_Fund_Trust_Fact_Sheet": "Stanbic Income Fund Trust",
    "faam_faif": "First Atlantic Income Fund",
    "faam_pips": "First Atlantic Personal Investment Plan",
}

FEE_COLUMNS = {
    "management": "management_fee_pct",
    "custody": "trustee_or_custody_fee_pct",
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


def num(v) -> float | None:
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def stem_of(filename: str) -> str:
    return re.sub(r"_?-?_?\d{4}-\d{2}\.pdf$", "", filename).strip("_-. ")


def build_timeline(points: list[tuple[str, float, str]]) -> list[dict]:
    """
    points: (as_of, rate, source_file) sorted ascending.
    Emit one segment per DISTINCT rate, not one per observation. A fee that
    holds steady for 20 months is one row, not twenty.
    """
    segments: list[dict] = []
    for as_of, rate, src in points:
        if segments and abs(segments[-1]["rate"] - rate) < 1e-9:
            continue                      # unchanged — extend the current segment
        if segments:
            prev = date.fromisoformat(as_of) - timedelta(days=1)
            segments[-1]["effective_to"] = prev.isoformat()
        segments.append({"rate": rate, "effective_from": as_of,
                         "effective_to": None, "source_file": src})
    return segments


def annual_ters(rows: list[dict]) -> list[dict]:
    """
    The December YTD figure IS that year's expense ratio. Earlier months are
    part-year and must never be published as an annual cost.
    """
    by_year: dict[int, tuple[str, float, str]] = {}
    latest: tuple[str, float, str] | None = None
    for r in rows:
        ter = num(r.get("ter_pct"))
        if ter is None:
            continue
        d = date.fromisoformat(r["as_of"])
        latest = (r["as_of"], ter, r["file"])
        if d.month == 12:
            by_year[d.year] = (r["as_of"], ter, r["file"])

    out = []
    for year, (as_of, ter, src) in sorted(by_year.items()):
        out.append({"rate": ter, "effective_from": f"{year}-01-01",
                    "effective_to": f"{year}-12-31", "source_file": src,
                    "conditions": f"Full-year expense ratio for {year} "
                                  f"(the December year-to-date figure)"})
    # the current, incomplete year
    if latest:
        as_of, ter, src = latest
        d = date.fromisoformat(as_of)
        if d.year not in by_year:
            out.append({"rate": ter, "effective_from": f"{d.year}-01-01",
                        "effective_to": None, "source_file": src,
                        "conditions": f"PART-YEAR: year-to-date at {as_of}, "
                                      f"NOT a full-year cost — do not compare "
                                      f"against an annual TER"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--navs", default="navs.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.navs, encoding="utf-8")))
    if not rows:
        print(f"{args.navs} is empty")
        return 1

    # Group by FUND, pooling every share class.
    by_fund: dict[str, list[dict]] = {}
    for r in rows:
        fund = FUND_OF.get(stem_of(r["file"]))
        if fund:
            by_fund.setdefault(fund, []).append(r)

    products = rest("GET", "/products?select=id,name,share_class")
    sources = rest("GET", "/sources?select=id,title")
    src_by_title = {s["title"]: s["id"] for s in sources}

    total = 0
    for fund, frows in sorted(by_fund.items()):
        frows.sort(key=lambda r: r["as_of"])
        classes = [p for p in products if p["name"] == fund]
        if not classes:
            print(f"  no product row for {fund} — skipped")
            continue

        plans: list[dict] = []
        for fee_type, column in FEE_COLUMNS.items():
            seen: dict[str, tuple[float, str]] = {}
            for r in frows:                       # dedupe classes on one date
                v = num(r.get(column))
                if v is not None and r["as_of"] not in seen:
                    seen[r["as_of"]] = (v, r["file"])
            pts = [(d, v, f) for d, (v, f) in sorted(seen.items())]
            for seg in build_timeline(pts):
                plans.append({**seg, "fee_type": fee_type, "conditions": None})
        for seg in annual_ters(frows):
            plans.append({**seg, "fee_type": "ter"})

        print(f"\n  {fund}  ({len(classes)} class(es))")
        for p in plans:
            span = f"{p['effective_from']} → {p['effective_to'] or 'current'}"
            note = ""
            if p["fee_type"] == "management" and len(
                    [x for x in plans if x["fee_type"] == "management"]) > 1:
                note = "  <- CHANGED"
            print(f"      {p['fee_type']:<11} {p['rate']:>5.2f}%  {span}{note}")

        if args.dry_run:
            continue

        for cls in classes:
            rest("DELETE", f"/product_fees?product_id=eq.{cls['id']}",
                 prefer="return=minimal")
            body = []
            for p in plans:
                sid = src_by_title.get(p["source_file"])
                if not sid:
                    continue
                body.append({
                    "product_id": cls["id"], "fee_type": p["fee_type"],
                    "rate": round(p["rate"] / 100.0, 8), "flat_minor": None,
                    "basis": "annual_nav", "conditions": p["conditions"],
                    "effective_from": p["effective_from"],
                    "effective_to": p["effective_to"],
                    "source_id": sid, "verified_on": p["effective_from"],
                })
            if body:
                rest("POST", "/product_fees", body)
                total += len(body)

    if args.dry_run:
        print("\nDry run — nothing written.")
    else:
        print(f"\n  {total} fee rows written across "
              f"{sum(len([p for p in products if p['name'] == f]) for f in by_fund)} "
              f"product/class rows")
        print("  Fees are fund-level: every class of a fund now carries the "
              "same timeline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

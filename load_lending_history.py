"""
load_lending_history.py — every Bank of Ghana lending return we hold, not just the latest.

WHY THIS EXISTS
extract_apr.py reads every return in data/apr — September 2024, March 2025,
June 2025 and May 2026 — into apr_banks.csv. load_lending_products.py then
keeps only the latest, because it maintains the CURRENT rate on each product.

So the three older returns were extracted and never loaded. Bank of Ghana no
longer publishes them, which makes them the most valuable thing in the
archive: nobody else can show how lending costs moved across those months.

WHY A SEPARATE TABLE AND A SEPARATE SCRIPT
The current rate lives on the product row and is read by every lending page.
History goes in lending_history, which nothing current reads, so loading it
cannot change a figure on /funding. And this script is the only writer of that
table — the lesson of the Treasury bill delete bug and the Stanbic overwrite,
applied before rather than after.

WHAT IT RECORDS
Each row as Bank of Ghana published it: bank name as printed in the return,
category, tenor, and the rates. A bank that did not report a cell is stored
as null, never zero. Keyed on (bank, category, tenor, as_of), so rerunning it
updates rather than duplicates.

Usage:
    python load_lending_history.py --dry-run
    python load_lending_history.py
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


def env() -> dict:
    out = {}
    if os.path.exists(".env.local"):
        for line in open(".env.local", encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    for k in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    if not out.get("SUPABASE_SERVICE_ROLE_KEY"):
        print("Missing Supabase credentials — run from the project root.")
        sys.exit(1)
    return out


E = env()
BASE = E["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = E["SUPABASE_SERVICE_ROLE_KEY"]


def call(method: str, path: str, body=None, prefer: str | None = None):
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
    )
    req.add_header("apikey", KEY)
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("Content-Type", "application/json")
    if prefer:
        req.add_header("Prefer", prefer)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        print(f"\n  {e.code} on {method} {path}")
        print(f"  {e.read().decode('utf-8', 'replace')[:500]}\n")
        raise


def num(v: str | None) -> float | None:
    """Blank or unparseable is null — a cell the bank did not report."""
    if v is None:
        return None
    v = v.strip()
    if not v or v.lower() in ("nan", "none", "-", "n/a"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def key(name: str) -> str:
    """So 'Bank of Africa Ghana Limited' in the return matches 'Bank of Africa Ghana'."""
    k = name.casefold()
    k = re.sub(r"[().,&]", " ", k)
    k = re.sub(r"\b(limited|ltd|plc|company|co|ghana|gh|the)\b", " ", k)
    return re.sub(r"\s+", " ", k).strip()


# Where Bank of Ghana names a bank differently from the site.
ALIASES = {"fbnbank": "first bank"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--banks-csv", default="apr_banks.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.banks_csv):
        print(f"  {args.banks_csv} not found. Run extract_apr.py first.")
        return 1

    with open(args.banks_csv, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    banks = call("GET", "/providers?select=id,trading_name&provider_type=eq.bank") or []
    by_key = {key(b["trading_name"]): b["id"] for b in banks}

    out: list[dict] = []
    unmatched: set[str] = set()
    for r in rows:
        bank = (r.get("bank") or "").strip()
        if not bank or not r.get("as_of"):
            continue
        pid = by_key.get(ALIASES.get(key(bank), key(bank)))
        if pid is None:
            unmatched.add(bank)
        tenor = num(r.get("tenor_years"))
        out.append(
            {
                "bank": bank,
                "provider_id": pid,
                "category": (r.get("category") or "").strip(),
                "tenor_years": int(tenor) if tenor is not None else 0,
                "as_of": r["as_of"],
                "avg_lending_rate": num(r.get("avg_lending_rate")),
                "average_apr": num(r.get("average_apr")),
                "reference_rate": num(r.get("grr")),
                "spread": num(r.get("spread")),
                "max_fees_total": num(r.get("max_fees_total")),
                "source_file": (r.get("source") or "").strip() or "unknown",
            }
        )

    by_date: dict[str, list[dict]] = {}
    for o in out:
        by_date.setdefault(o["as_of"], []).append(o)

    print()
    print(f"  {len(out)} rows from {len(by_date)} returns")
    for d in sorted(by_date):
        reported = sum(1 for o in by_date[d] if o["average_apr"] is not None)
        print(f"    {d}   {len(by_date[d]):>4} cells, {reported:>4} with an APR reported")

    if unmatched:
        print()
        print("  Bank names in the returns with no provider on the site:")
        for b in sorted(unmatched):
            print(f"    {b}")
        print("  Loaded anyway, with no provider link. Worth matching by hand.")

    if args.dry_run:
        print()
        print("  Dry run — nothing written.")
        return 0

    written = 0
    for i in range(0, len(out), 200):
        batch = out[i : i + 200]
        call(
            "POST",
            "/lending_history?on_conflict=bank,category,tenor_years,as_of",
            batch,
            prefer="return=minimal,resolution=merge-duplicates",
        )
        written += len(batch)

    print()
    print(f"  {written} rows written to lending_history")
    return 0


if __name__ == "__main__":
    sys.exit(main())

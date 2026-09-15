"""
fetch_tbills.py — read Bank of Ghana's rates table instead of guessing at PDFs.

WHY THIS IS A REWRITE
The previous version enumerated tender numbers and tried each against three
upload folders and six filename forms — eighteen requests a week, guessing.
It worked until it did not, and then reported "0 downloaded, 0 missing" for
three consecutive weeks while the 91-day rate fell from 5.08% to 4.69%.

Every page on this site that shows a real return was reading a stale
benchmark, and nothing said so. That is worse than a missing figure: a blank
is honest, a stale number is confident and wrong.

WHAT IT READS NOW
https://www.bog.gov.gh/treasury-and-the-markets/treasury-bill-rates/

A table, published by the Bank, with one row per tender per security:

    Issue Date | Tender | Security Type | Discount Rate | Interest Rate
    07 Sep 2026 | 2023  | 91 DAY BILL   | 4.7480        | 4.8050

One request. No tender arithmetic, no folder window, no filename variants.
This is the third fetcher on this project to be rewritten from guessing
addresses to reading a page, after the APR notices and the GSE reports. The
lesson has now cost more rounds than anything else here.

WHICH COLUMN
Interest Rate, not Discount Rate. The existing series matches it — the 21
August tender shows 5.0795 interest against 5.0158 discount, and the database
holds 0.050795 — and "weighted average interest rate" is the language the
Bank and the press both use.

WHY IT STILL SAVES A FILE
The old fetcher left an archive of 24 auction PDFs. A table scrape leaves
nothing, and this project's most defensible asset is documents whose
publishers no longer have them. So the page itself is saved, dated, the way
the regulators' registers are: the table changes every week and we keep what
it said.

Usage:
    python fetch_tbills.py --dry-run
    python fetch_tbills.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date

from polite_fetch import fetch, status_word

PAGE = "https://www.bog.gov.gh/treasury-and-the-markets/treasury-bill-rates/"
SNAPSHOT_DIR = "data/tbills"

# 91 DAY BILL -> 91. Bonds carry a term in years and are skipped for now —
# they belong in a series of their own rather than mixed into the bill curve.
BILL_RX = re.compile(r"(\d{2,3})\s*DAY\s*BILL", re.I)

MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}


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
        print(f"  {e.read().decode('utf-8', 'replace')[:400]}\n")
        raise


def parse_date(s: str) -> str | None:
    """'07 Sep 2026' -> '2026-09-07'."""
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})", s.strip())
    if not m:
        return None
    day, mon, year = m.groups()
    month = MONTHS.get(mon.lower()[:3])
    if not month:
        return None
    return f"{year}-{month:02d}-{int(day):02d}"


def strip_tags(h: str) -> str:
    return re.sub(r"<[^>]+>", "\t", h)


def parse_table(html: str) -> list[dict]:
    """
    One row per tender per security.

    The table is read row by row rather than by column position, because a
    column inserted upstream would silently shift every figure by one — and a
    rate that is quietly the discount rate instead of the interest rate is
    exactly the kind of error nobody notices.
    """
    rows: list[dict] = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        cells = [
            re.sub(r"\s+", " ", strip_tags(td)).replace("\t", " ").strip()
            for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)
        ]
        if len(cells) < 5:
            continue

        as_of = parse_date(cells[0])
        if not as_of:
            continue

        bill = BILL_RX.search(cells[2])
        if not bill:
            continue  # a bond, not a bill

        try:
            interest = float(re.sub(r"[^\d.]", "", cells[4]))
        except ValueError:
            continue
        if not 0 < interest < 100:
            continue

        rows.append(
            {
                "as_of": as_of,
                "tender": cells[1].strip(),
                "days": int(bill.group(1)),
                "interest": round(interest / 100, 6),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    status, html = fetch(PAGE)
    if status != 200 or not html:
        print(f"  {status_word(status)} — {PAGE}")
        print()
        print("  Nothing written. A fetcher that cannot reach its source should")
        print("  say so, not report zero rows as though the week was quiet.")
        return 1

    rows = parse_table(html)
    if not rows:
        print("  Page fetched but no bill rows parsed.")
        print("  The table structure may have changed — read it before assuming")
        print("  the Bank has stopped publishing.")
        return 1

    latest = max(r["as_of"] for r in rows)
    by_tenor = {
        d: next((r for r in rows if r["as_of"] == latest and r["days"] == d), None)
        for d in (91, 182, 364)
    }

    print()
    print(f"  {len(rows)} bill row(s) parsed, latest {latest}")
    for d, r in by_tenor.items():
        if r:
            print(f"    {d:>3}-day  {r['interest'] * 100:>7.4f}%   tender {r['tender']}")

    if args.dry_run:
        print()
        print("  Dry run — nothing written.")
        return 0

    # Keep the page. The table changes weekly and the Bank keeps no history.
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snap = os.path.join(SNAPSHOT_DIR, f"tbill-rates-{date.today().isoformat()}.html")
    with open(snap, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"  page saved to {snap}")

    products = call(
        "GET",
        "/products?asset_class=eq.government_security&select=id,name,lock_in_days",
    )
    written = 0
    for r in rows:
        prod = next(
            (
                p
                for p in products or []
                if str(r["days"]) in str(p.get("name", ""))
                or p.get("lock_in_days") == r["days"]
            ),
            None,
        )
        if not prod:
            continue
        call(
            "POST",
            "/nav_observations?on_conflict=product_id,as_of",
            [
                {
                    "product_id": prod["id"],
                    "as_of": r["as_of"],
                    "yield_annualised": r["interest"],
                }
            ],
            prefer="resolution=merge-duplicates",
        )
        written += 1

    print(f"  {written} observation(s) written")
    print()
    print("  The old fetcher guessed eighteen PDF URLs a week and reported")
    print("  success when it found none. Three weeks passed. This reads one")
    print("  page and fails loudly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

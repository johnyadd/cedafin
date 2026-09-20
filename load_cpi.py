"""
load_cpi.py — fourteen months of Ghanaian inflation.

WHY THIS MATTERS MORE THAN IT LOOKS
Every return on this site is a nominal figure. A fund returning 38.80% tells
you what the units did, not what the money bought. In a country where
inflation was 13.7% eighteen months ago and 5.0% now, the difference between
nominal and real is the whole question.

And it produces one finding immediately. The 91-day Treasury bill pays 5.08%.
Inflation in August 2026 was 5.0%. A saver in the shortest bill is earning
almost nothing in real terms — and that is the product a cautious Ghanaian is
most often steered towards.

WHY THIS IS A LOADER AND NOT A FETCHER
The Ghana Statistical Service publishes the CPI monthly at statsghana.gov.gh,
and a fetcher pointed at their bulletin URL pattern would be the right long-term
answer. We do not know that pattern, and guessing at it would produce a script
that silently fetches nothing.

So these figures are entered from the published releases, each one traceable to
a GSS statement reported at the time. The next step is to watch one release
land, learn the URL shape, and automate it.

WHY THE FIGURES ARE WHAT THEY ARE
Ghanaian inflation fell for fifteen consecutive months to March 2026, reaching
the lowest level in about three decades, before ticking up again through the
middle of the year. That shape is why a single recent reading is misleading and
a series is not: a fund's return has to be set against the inflation of its own
period, not against this month's.

Usage:
    python load_cpi.py --dry-run
    python load_cpi.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

SERIES = "GH_CPI_YOY"

# Year-on-year headline inflation, as published by the Ghana Statistical
# Service. Stored as decimals to match the rest of macro_series.
#
# Each is the figure GSS announced for that month. Where a month is absent we
# have left it absent rather than interpolating — a made-up point in an
# inflation series would quietly corrupt every real return computed across it.
CPI = [
    # May 2024 to May 2025, added 19 September 2026 from the historical
    # tables printed inside two GSS CPI press releases — the August 2025
    # release carries Aug-24 to May-25, the May 2025 release the three
    # months before that. Both are GSS's own documents.
    #
    # This took the series from 15 months to 28, and the number of products
    # whose observations predate the CPI from 46 to 7. Fifty products now
    # carry a real return where eight did that morning.
    #
    # The seam at May/June 2025 is not an overlap, so nothing cross-checks
    # it directly. But August 2025 appears in both halves at 11.5%, and the
    # disinflation runs continuously through the join.
    ("2024-05-31", 0.231),
    ("2024-06-30", 0.228),
    ("2024-07-31", 0.209),
    ("2024-08-31", 0.204),
    ("2024-09-30", 0.215),
    ("2024-10-31", 0.221),
    ("2024-11-30", 0.230),
    ("2024-12-31", 0.238),
    ("2025-01-31", 0.235),
    ("2025-02-28", 0.231),
    ("2025-03-31", 0.224),
    ("2025-04-30", 0.212),
    ("2025-05-31", 0.184),
    ("2025-06-30", 0.137),
    ("2025-07-31", 0.121),
    ("2025-08-31", 0.115),
    ("2025-09-30", 0.094),
    ("2025-10-31", 0.080),
    ("2025-11-30", 0.063),
    ("2025-12-31", 0.054),
    ("2026-01-31", 0.038),
    ("2026-02-28", 0.033),
    ("2026-03-31", 0.032),
    ("2026-04-30", 0.034),
    ("2026-05-31", 0.037),
    ("2026-06-30", 0.053),
    ("2026-07-31", 0.046),
    ("2026-08-31", 0.050),
]

SOURCE = {
    "kind": "regulator_publication",
    "publisher": "Ghana Statistical Service",
    "title": "Consumer Price Index — monthly year-on-year inflation, Jun 2025 to Aug 2026",
    "url": "https://statsghana.gov.gh/",
    "retrieved_at": "2026-09-03",
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
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        print(f"  {len(CPI)} monthly observation(s), {CPI[0][0]} to {CPI[-1][0]}")
        print()
        for d, v in CPI:
            bar = "#" * round(v * 100)
            print(f"    {d}   {v*100:>5.1f}%  {bar}")
        print()
        print()
        print("  These figures used to be compared here against the T-bill"
              " and a fund, with all three typed in.")
        print("  They went stale: the 91-day bill was 5.08% when that was"
              " written and 4.70% now, which flipped the")
        print("  conclusion from a small positive real return to a"
              " negative one. The comparison belongs on a page that")
        print("  reads both numbers live, not in a loader.")
        return 0

    src = call("GET", f"/sources?url=eq.{SOURCE['url']}&kind=eq.{SOURCE['kind']}&select=id")
    if src:
        source_id = src[0]["id"]
    else:
        made = call("POST", "/sources", SOURCE, prefer="return=representation")
        source_id = made[0]["id"]
    print(f"  source {source_id}")

    added = updated = 0
    for as_of, value in CPI:
        have = call(
            "GET",
            # No id column — the key is series_code plus as_of.
            f"/macro_series?series_code=eq.{SERIES}&as_of=eq.{as_of}&select=value",
        )
        if have:
            if abs(float(have[0]["value"]) - value) > 1e-9:
                call(
                    "PATCH",
                    f"/macro_series?series_code=eq.{SERIES}&as_of=eq.{as_of}",
                    {"value": value, "source_id": source_id},
                )
                updated += 1
                print(f"    updated {as_of}  {value*100:.1f}%")
            continue
        call(
            "POST",
            "/macro_series",
            {
                "series_code": SERIES,
                "as_of": as_of,
                "value": value,
                "source_id": source_id,
            },
        )
        added += 1

    total = call("GET", f"/macro_series?series_code=eq.{SERIES}&select=as_of")
    print()
    print(f"  {added} added, {updated} corrected — {len(total)} point(s) held")
    print()
    print("  Every nominal return on this site can now be set against the")
    print("  inflation of its own period rather than against nothing.")
    print()
    print("  Next: watch a GSS release land, learn the bulletin URL pattern,")
    print("  and replace this loader with a fetcher.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

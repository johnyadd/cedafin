"""
fetch_cpi_index.py — Ghana's consumer price index, back to 1960.

WHY THIS AND NOT THE MONTHLY SERIES WE ALREADY HAVE
load_cpi.py holds fifteen months of year-on-year inflation, which is what a
real-return calculation needs: a rate over a period.

A purchasing-power calculator needs something different — the price LEVEL at
two points in time, so the ratio between them gives the answer. "What is
GH₵1,000 from 2010 worth today" is index_now / index_2010, and no amount of
recent rates substitutes for a level going back decades.

WHY THE WORLD BANK RATHER THAN THE GHANA STATISTICAL SERVICE
GSS is the primary source and publishes monthly. Their historical archive is
spread across PDF bulletins going back years, which is a scraping project.

The World Bank publishes an annual index for Ghana on a documented JSON API,
sourced from the IMF's International Financial Statistics, which in turn takes
it from GSS. One fetch instead of a hundred PDFs, at annual granularity — which
is what every purchasing-power calculator uses anyway, because nobody asks what
their money was worth in March 1987.

WHAT THE INDEX MEANS
2010 = 100. A value of 400 means prices are four times their 2010 level. The
ratio between any two years is all the calculator needs; the base year cancels
out and never appears on screen.

WHAT THIS CANNOT TELL ANYONE
The redenomination. Ghana dropped four zeroes from the cedi in July 2007, so
GH₵1 replaced ¢10,000. The index is continuous across it because it measures
prices rather than currency units, but an answer spanning 2007 needs saying
plainly or it will look absurd. The calculator page has to handle that; this
fetcher only records it.

Usage:
    python fetch_cpi_index.py --dry-run
    python fetch_cpi_index.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

SERIES = "GH_CPI_INDEX"
API = (
    "https://api.worldbank.org/v2/country/gha/indicator/FP.CPI.TOTL"
    "?format=json&per_page=200"
)

SOURCE = {
    "kind": "regulator_publication",
    "publisher": "World Bank / IMF International Financial Statistics",
    "title": "Ghana consumer price index (2010 = 100), annual",
    "url": "https://data.worldbank.org/indicator/FP.CPI.TOTL?locations=GH",
    "retrieved_at": None,  # set at run time
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


def fetch_index() -> list[tuple[int, float]]:
    """Year and index level, oldest first, missing years dropped."""
    req = urllib.request.Request(
        API, headers={"User-Agent": "CedafinBot/0.2 (comparison site)"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read())

    # The v2 API returns [metadata, rows]. A bare list of one element means an
    # error message rather than data.
    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError(f"unexpected API response: {str(payload)[:200]}")

    rows = payload[1] or []
    out = []
    for row in rows:
        v = row.get("value")
        if v is None:
            continue
        out.append((int(row["date"]), float(v)))
    out.sort()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("  fetching Ghana CPI index from the World Bank ...")
    series = fetch_index()
    if not series:
        print("  nothing returned — the indicator or country code may have changed")
        return 1

    first_y, first_v = series[0]
    last_y, last_v = series[-1]
    print(f"  {len(series)} year(s), {first_y} to {last_y}")
    print()

    if args.dry_run:
        # A few landmarks rather than sixty lines.
        marks = [y for y in (1990, 2000, 2007, 2010, 2015, 2020, last_y)]
        idx = dict(series)
        print("    year    index    GH¢100 then, in today's money")
        for y in marks:
            if y not in idx:
                continue
            worth = 100 * (last_v / idx[y])
            print(f"    {y}   {idx[y]:>8.1f}   GH¢{worth:>12,.2f}")
        print()
        print(f"    Prices are {last_v / idx.get(2010, last_v):.1f}x their 2010 level.")
        print()
        print("    NOTE: Ghana redenominated in July 2007 — GH¢1 replaced ¢10,000.")
        print("    The index is continuous across it because it measures prices,")
        print("    not currency units, but any answer spanning 2007 has to say so.")
        return 0

    from datetime import date

    SOURCE["retrieved_at"] = date.today().isoformat()
    src = call(
        "GET", f"/sources?url=eq.{SOURCE['url']}&kind=eq.{SOURCE['kind']}&select=id"
    )
    if src:
        source_id = src[0]["id"]
    else:
        made = call("POST", "/sources", SOURCE, prefer="return=representation")
        source_id = made[0]["id"]
    print(f"  source {source_id}")

    added = updated = 0
    for year, value in series:
        # Year-end, so it sorts alongside the monthly series without colliding.
        as_of = f"{year}-12-31"
        have = call(
            "GET",
            f"/macro_series?series_code=eq.{SERIES}&as_of=eq.{as_of}&select=value",
        )
        if have:
            if abs(float(have[0]["value"]) - value) > 1e-6:
                call(
                    "PATCH",
                    f"/macro_series?series_code=eq.{SERIES}&as_of=eq.{as_of}",
                    {"value": value, "source_id": source_id},
                )
                updated += 1
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

    print(f"  {added} added, {updated} corrected")
    print()
    print(f"  Ghana's price level is now on file from {first_y} to {last_y}.")
    print("  A purchasing-power calculator has something to work with.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

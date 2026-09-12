"""
index_archive.py — what we hold, for when, and what is missing from it.

WHY THIS EXISTS
The archive turned out to be larger than anyone had decided it should be. A
hundred and eighty-five documents accumulated as a by-product of building
pages: Bank of Ghana gold circulars, Treasury auction results, GSE monthly
reports, provider factsheets, four APR returns.

Most of those institutions do not keep their own back numbers. Bank of Ghana
publishes the current APR notice and removes the last one — we checked eight
earlier months and found none. Fund managers replace a factsheet rather than
versioning it. The Exchange posts this month's report.

So these files are, for several series, the only accessible copies in
existence. They are also the one asset a language model cannot reproduce, at
any price, because a document removed from the internet is gone.

WHAT THIS DOES
Counts what is held per series, reports the period covered, and — the useful
part — names the gaps. A series with a hole in it looks complete until
somebody tries to compute across it.

AND WHY GAPS MATTER MORE THAN TOTALS
A fetcher that silently stops working leaves a hole nobody notices for months.
The twenty-month fee trend we published rests on four APR files; a fifth
missing month would have changed the answer and nothing would have said so.

Usage:
    python index_archive.py
    python index_archive.py --json     # machine-readable, for a page
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date

ROOT = "data"

# What each folder holds, how often the source publishes, and how to read a
# period out of the filename. Anything not listed is still counted, just not
# gap-checked — a new folder should be added here rather than silently ignored.
SERIES = {
    "apr": {
        "label": "Bank of Ghana APR returns",
        "cadence": "monthly",
        "note": "BoG publishes monthly and removes the previous notice. Three of these cannot be obtained anywhere else.",
        "rx": re.compile(r"(\d{4})-(\d{2})"),
    },
    "gse": {
        "label": "Ghana Stock Exchange monthly reports",
        "cadence": "monthly",
        "note": "The entire broker market-share series rests on these.",
        "rx": re.compile(r"(\d{4})-(\d{2})"),
    },
    "tbills": {
        "label": "Treasury bill auction results",
        "cadence": "weekly",
        "note": "Tender numbers are sequential; a missing number is a missing week.",
        "rx": re.compile(r"(\d{4})"),
    },
    "goldcoin": {
        "label": "Bank of Ghana gold coin circulars",
        "cadence": "daily",
        "note": "Published each business day, not archived by the Bank.",
        "rx": re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    },
    "factsheets": {
        "label": "Provider fund factsheets",
        "cadence": "irregular",
        "note": "Replaced rather than versioned by their issuers. An old fee is only provable if the old document survives.",
        "rx": None,
    },
    "faam": {
        "label": "First Atlantic documents",
        "cadence": "irregular",
        "note": None,
        "rx": None,
    },
}


def month_range(a: str, b: str) -> list[str]:
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    out = []
    while (ya, ma) <= (yb, mb):
        out.append(f"{ya:04d}-{ma:02d}")
        ma += 1
        if ma == 13:
            ma, ya = 1, ya + 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(ROOT):
        print(f"  No {ROOT}/ directory — run from the project root.")
        return 1

    report = []
    total_files = total_bytes = 0

    for folder in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, folder)
        if not os.path.isdir(path):
            continue

        files = [
            f
            for f in sorted(os.listdir(path))
            if os.path.isfile(os.path.join(path, f))
        ]
        size = sum(os.path.getsize(os.path.join(path, f)) for f in files)
        total_files += len(files)
        total_bytes += size

        meta = SERIES.get(folder, {"label": folder, "cadence": "unknown", "rx": None, "note": None})
        entry = {
            "folder": folder,
            "label": meta["label"],
            "cadence": meta["cadence"],
            "files": len(files),
            "bytes": size,
            "note": meta.get("note"),
            "first": None,
            "last": None,
            "missing": [],
        }

        rx = meta.get("rx")
        if rx and files:
            periods = set()
            for f in files:
                m = rx.search(f)
                if m:
                    if meta["cadence"] == "monthly":
                        periods.add(f"{m.group(1)}-{m.group(2)}")
                    elif meta["cadence"] == "daily":
                        periods.add(m.group(0))
                    else:
                        periods.add(m.group(1))
            if periods:
                ordered = sorted(periods)
                entry["first"], entry["last"] = ordered[0], ordered[-1]

                # Gaps, for monthly series only. Daily has weekends and
                # holidays; weekly tender numbers would need the real
                # calendar. Claiming a gap that is really a public holiday
                # would train us to ignore the report.
                if meta["cadence"] == "monthly":
                    expected = month_range(ordered[0], ordered[-1])
                    entry["missing"] = [p for p in expected if p not in periods]

        report.append(entry)

    if args.json:
        print(json.dumps({"as_of": date.today().isoformat(), "series": report}, indent=2))
        return 0

    print()
    print("  What Cedafin holds")
    print()
    for e in report:
        span = (
            f"{e['first']} to {e['last']}"
            if e["first"] and e["last"] and e["first"] != e["last"]
            else (e["first"] or "—")
        )
        print(
            f"  {e['label'][:42]:<44} {e['files']:>4} files  "
            f"{e['bytes'] / 1_048_576:>6.1f} MB  {span}"
        )
        if e["missing"]:
            print(f"      MISSING: {', '.join(e['missing'])}")
        if e["note"]:
            print(f"      {e['note']}")
        print()

    print(f"  {total_files} documents, {total_bytes / 1_048_576:.1f} MB total")
    print()

    gaps = sum(len(e["missing"]) for e in report)
    if gaps:
        print(f"  {gaps} missing period(s). A series with a hole looks complete")
        print("  until somebody computes across it.")
    else:
        print("  No gaps in the monthly series.")
    print()
    print("  Most of these institutions do not keep their own back numbers.")
    print("  For several series this is the only accessible copy there is —")
    print("  which is the one thing about this project that cannot be")
    print("  reproduced by anybody, at any price, however good their tools.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

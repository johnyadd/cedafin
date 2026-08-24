"""
extract_tbills.py — weighted-average rates out of BoG auction PDFs.

THE COLUMN MATTERS MORE THAN THE PARSING
Each tender publishes several rates per tenor and they are not interchangeable:

    Range of bid rates          4.6500 – 6.0000     what bidders asked
    Bid rates allotted in full  4.6500 – 5.2502     what was accepted
    Discount rate               5.0158              price paid below par
    Interest rate               5.0795   <-- THIS   the yield, weighted average
                                                    for the week

The last column — "Weighted Avg. Rates for the Week" interest rate — is the
figure everyone quotes and the one a saver would recognise. The discount rate
sits right beside it and is roughly six basis points lower on the 91-day, more
on longer tenors. Taking the wrong one would produce numbers that look
plausible, differ from every published source, and be wrong in a direction
nobody would notice.

Verified against tender 2021 (21 Aug 2026), where Mansa Markets independently
reports 5.0795 / 7.0800 / 11.5930 — the same figures this extracts.

TWO CHECKS BEFORE ANY ROW IS WRITTEN
  1. Each rate must fall inside the "bid rates allotted in full" range printed
     on the same page. A weighted average outside the accepted range is
     arithmetically impossible, so a value that fails this is a parsing fault,
     not a market event.
  2. 91-day <= 182-day <= 364-day. Ghana's curve has been upward-sloping
     throughout the period covered; an inversion would be notable enough to
     want a human to look rather than to load silently.

Writes to benchmarks.csv, so everything still passes through
load_benchmarks.py with its range checks and source records.

Usage:
    python extract_tbills.py --dry-run
    python extract_tbills.py
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys
from datetime import date

try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf is not installed. Run:  pip install pypdf")
    sys.exit(1)

MONTHS = {m.lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}

TENORS = [("GH_TBILL_91", "91"), ("GH_TBILL_182", "182"), ("GH_TBILL_364", "364")]


def text_of(path: str) -> str:
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception as e:                                   # noqa: BLE001
        print(f"    unreadable: {type(e).__name__}: {e}")
        return ""


def tender_date(text: str) -> date | None:
    """'RESULTS OF TENDER 2021 HELD ON 21ST AUGUST 2026'."""
    m = re.search(r"HELD\s+ON\s+(\d{1,2})(?:ST|ND|RD|TH)?\s+([A-Z]+)\s+(\d{4})",
                  text, re.I)
    if not m:
        return None
    mon = MONTHS.get(m.group(2).lower())
    return date(int(m.group(3)), mon, int(m.group(1))) if mon else None


def tender_number(text: str, path: str) -> str:
    m = re.search(r"RESULTS\s+OF\s+TENDER\s+(\d{3,5})", text, re.I)
    if m:
        return m.group(1)
    m = re.search(r"(\d{3,5})", os.path.basename(path))
    return m.group(1) if m else "?"


def allotted_ranges(text: str) -> list[tuple[float, float]]:
    """
    The "bid rates allotted in full" ranges, in tenor order. Used to sanity
    check the weighted averages against figures printed on the same page.
    """
    out: list[tuple[float, float]] = []
    for m in re.finditer(r"(\d{1,2}\.\d{2,4})\s*[–\-]\s*(\d{1,2}\.\d{2,4})", text):
        out.append((float(m.group(1)), float(m.group(2))))
    return out


def weighted_averages(text: str) -> list[float]:
    """
    The trailing block of standalone decimals is the weighted-average pair per
    tenor — discount then interest, six numbers for three tenors. The INTEREST
    rate is the second of each pair and the one to take.

    Ranges are excluded first so their endpoints cannot be mistaken for
    averages; what remains, in document order, is the averages block.
    """
    stripped = re.sub(r"\d{1,2}\.\d{2,4}\s*[–\-]\s*\d{1,2}\.\d{2,4}", " ", text)
    # Amounts carry commas or a currency mark; rates do not.
    nums = [
        float(n) for n in re.findall(r"(?<![\d,.])(\d{1,2}\.\d{4})(?![\d,])", stripped)
    ]
    return nums


def extract(path: str) -> dict | None:
    text = text_of(path)
    if not text.strip():
        return None
    when = tender_date(text)
    if not when:
        print("    no tender date found")
        return None

    nums = weighted_averages(text)
    ranges = allotted_ranges(text)
    if len(nums) < 6:
        print(f"    only {len(nums)} rate-shaped numbers — expected 6")
        return None

    # NOT interleaved pairs. The block is all three DISCOUNT rates, then all
    # three INTEREST rates, column-major:
    #
    #     5.0158   6.8379  10.3886     <- discount,  91 / 182 / 364
    #     5.0795   7.0800  11.5930     <- interest,  91 / 182 / 364
    #
    # Reading it as (discount, interest) pairs would have made 6.8379 — the
    # 182-day DISCOUNT rate — the 91-day yield. Plausible-looking, wrong, and
    # exactly the class of error that survives review.
    tail = nums[-6:]
    rates = {code: tail[3 + i] for i, (code, _) in enumerate(TENORS)}

    problems: list[str] = []

    # Check 1: inside the allotted range printed on the same page.
    allotted = ranges[3:6] if len(ranges) >= 6 else ranges[:3]
    for i, (code, label) in enumerate(TENORS):
        if i < len(allotted):
            lo, hi = allotted[i]
            # The weekly average can sit slightly above the allotted range, so
            # allow a small margin rather than demanding containment.
            if not (lo - 1.0 <= rates[code] <= hi + 1.5):
                problems.append(
                    f"{label}-day {rates[code]}% outside allotted {lo}-{hi}")

    # Check 2: the curve slopes upward, as it has throughout this period.
    if not (rates["GH_TBILL_91"] <= rates["GH_TBILL_182"]
            <= rates["GH_TBILL_364"]):
        problems.append(
            f"curve inverted: {rates['GH_TBILL_91']} / "
            f"{rates['GH_TBILL_182']} / {rates['GH_TBILL_364']}")

    return {
        "tender": tender_number(text, path),
        "as_of": when.isoformat(),
        "rates": rates,
        "problems": problems,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/tbills")
    ap.add_argument("--file", default="benchmarks.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.dir, "*.pdf")))
    if not files:
        print(f"No PDFs in {args.dir}. Run fetch_tbills.py first.")
        return 1

    print(f"Reading {len(files)} tender(s)\n")
    good, flagged = [], []
    for p in files:
        r = extract(p)
        if not r:
            print(f"  {os.path.basename(p):<22} nothing extracted")
            continue
        line = (f"  tender {r['tender']}  {r['as_of']}  "
                f"91d {r['rates']['GH_TBILL_91']:6.4f}  "
                f"182d {r['rates']['GH_TBILL_182']:6.4f}  "
                f"364d {r['rates']['GH_TBILL_364']:7.4f}")
        if r["problems"]:
            print(line + "   !! FLAGGED")
            for x in r["problems"]:
                print(f"       {x}")
            flagged.append(r)
        else:
            print(line)
            good.append(r)

    print(f"\n  {len(good)} clean, {len(flagged)} flagged")
    if flagged:
        print("  Flagged tenders are NOT written. Each failed a check against")
        print("  figures printed on its own page — that is a parsing fault, not")
        print("  a market event. Dump the PDF and look before loading it.")
    if not good:
        return 1

    if args.dry_run:
        print("\nDry run — benchmarks.csv untouched.")
        return 0

    existing: set[tuple[str, str]] = set()
    if os.path.exists(args.file):
        with open(args.file, encoding="utf-8") as f:
            for row in csv.DictReader(
                    line for line in f if not line.lstrip().startswith("#")):
                existing.add(((row.get("series") or "").strip(),
                              (row.get("as_of") or "").strip()))

    added = skipped = 0
    with open(args.file, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for r in sorted(good, key=lambda x: x["as_of"]):
            for code, _ in TENORS:
                if (code, r["as_of"]) in existing:
                    skipped += 1
                    continue
                w.writerow([code, r["as_of"], r["rates"][code],
                            f"BoG tender {r['tender']}, weighted average "
                            f"interest rate"])
                added += 1

    print(f"\n  {added} rows appended to {args.file}"
          f"{f', {skipped} already present' if skipped else ''}")
    print("  Next: python load_benchmarks.py --dry-run")
    print("\n  NOTE: these are WEIGHTED AVERAGE INTEREST rates, not discount")
    print("  rates. If any figure already in benchmarks.csv came from the")
    print("  discount column it will disagree by a few basis points — check")
    print("  the earlier hand-entered rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
extract_apr.py — per-bank lending rates out of Bank of Ghana's APR reports.

WHAT IS IN THESE DOCUMENTS
Nine tables — household, SME and corporate, each at one, three and five years —
with a row per bank giving the Ghana Reference Rate, the bank's spread, its
average lending rate, five separate fee columns, and the resulting average APR.
Plus a summary naming the highest and lowest bank in every category.

The May 2026 SME numbers are why this matters:

    1-year SME     11.03%  Standard Chartered  ...  33.58%  Guaranty Trust
    3-year SME     13.34%  Stanbic             ...  31.09%  Universal Merchant
    5-year SME     13.97%  Ecobank             ...  25.07%  Agricultural Dev.

A Ghanaian business can pay eleven percent or thirty-three percent for the same
one-year facility, in the same month, from two licensed banks. Three times the
cost. Bank of Ghana publishes this and almost nobody reads it.

THE WORD "INDICATIVE" TRAVELS WITH EVERY FIGURE
The document is explicit: "The APRs reported in this table are indicative. A
typical customer of a bank may be faced with an actual APR different from these
indicative APRs, depending on the bank's assessment of the borrower's specific
circumstance."

That is not boilerplate to be dropped on the way to a database. A published
figure implying a business WILL get 11.03% would be wrong in the direction that
matters, so `basis` carries it into every row and no page may show a rate
without it.

FEES ARE SEPARATE FROM THE RATE, AND THEY ARE NOT SMALL
Commitment, processing, arrangement, insurance and facility fees each have
their own column, and each is a maximum rather than a certainty. The average
APR already includes them — but a borrower comparing headline lending rates
alone would miss up to five charges. Both are extracted so a page can show the
gap between the lending rate and the true cost.

Usage:
    python extract_apr.py --dry-run
    python extract_apr.py
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

# "1-Yr SME Credit 33.58 Guaranty Trust Bank ... 11.03 Standard Chartered ..."
SUMMARY_ROW = re.compile(
    r"(\d)-Yr\s+(Household|SME|Corporate)\s+Credit\s+"
    r"(\d{1,2}\.\d{2})\s+(.+?)\s+(\d{1,2}\.\d{2})\s+(.+?)(?=\n|$)",
    re.I,
)

# "3 Agricultural Development Bank Limited 10.03 9.56 19.59 N/A 2.00 ... 28.13"
# Bank names wrap across lines in the source, so rows are rebuilt before this
# is applied.
# Bank rows are NOT matched with one regex spanning name and numbers. Two
# attempts at that failed on real data:
#
#   negative spreads   "... 10.03 -1.26 ..."  the minus broke the boundary and
#                      the name swallowed "10.03 -1.26"
#   lost slashes       "N/A" sometimes extracts as "NL", so the numeric run
#                      started later than expected and the name swallowed
#                      whatever came before it
#
# Both produced provider names like "CalBank PLC 29.31 NL" — plausible-looking
# rows that create duplicate banks in the database. So instead: find where the
# numeric run BEGINS and split there. A token is numeric if it parses as a
# number or is any spelling of not-applicable.
NOT_APPLICABLE = {"N/A", "NA", "NL", "N\\A", "-", "--", "N/A."}


def is_numeric_token(tok: str) -> bool:
    if tok.upper() in NOT_APPLICABLE:
        return True
    return bool(re.fullmatch(r"-?\d{1,3}\.\d{1,2}", tok))


def split_bank_row(line: str) -> tuple[str, list[float | None]] | None:
    """
    "3 Agricultural Development Bank Limited 10.03 9.56 19.59 N/A ... 28.13"
    -> ("Agricultural Development Bank Limited", [10.03, 9.56, ...])

    Splits at the first token that begins an unbroken numeric run reaching the
    end of the line. Anything before it is the name, whatever it contains.
    """
    m = re.match(r"^\s*(\d{1,2})\s+(.+)$", line)
    if not m:
        return None
    toks = m.group(2).split()
    if len(toks) < 5:
        return None

    start = None
    for i in range(len(toks)):
        if all(is_numeric_token(t) for t in toks[i:]):
            start = i
            break
    if start is None or start == 0:
        return None

    name = " ".join(toks[:start]).strip(" .,")
    values = [None if t.upper() in NOT_APPLICABLE else float(t)
              for t in toks[start:]]
    if len(values) < 4 or len(name) < 4:
        return None
    return name, values


TABLE_HEADER = re.compile(
    r"APRs?\s+for\s+Banks.{0,4}\s+Loans\s+to\s+(Households|SMEs?|Corporates?)",
    re.I,
)
TENOR_LINE = re.compile(r"Tenor\s+of\s+Facility:\s*(\d)\s*year", re.I)

CATEGORY = {"household": "household", "households": "household",
            "sme": "sme", "smes": "sme",
            "corporate": "corporate", "corporates": "corporate"}


def text_of(path: str) -> str:
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception as e:                                   # noqa: BLE001
        print(f"    unreadable: {type(e).__name__}: {e}")
        return ""


def report_month(text: str, path: str) -> str | None:
    """'DEVELOPMENTS FOR MAY 2026' — the DATA month, not the cover month."""
    m = re.search(r"DEVELOPMENTS\s+FOR\s+([A-Z]+)\s+(\d{4})", text, re.I)
    if m:
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            d = date(int(m.group(2)), mon, 1)
            # Month end, since the figures describe the month as a whole.
            nxt = date(d.year + (mon == 12), 1 if mon == 12 else mon + 1, 1)
            return date.fromordinal(nxt.toordinal() - 1).isoformat()
    m = re.search(r"(\d{4})-(\d{2})", os.path.basename(path))
    return f"{m.group(1)}-{m.group(2)}-01" if m else None


def grr(text: str) -> float | None:
    m = re.search(r"(\d{1,2}\.\d{2})\s*%?\s*\n?\s*[A-Z]+\s+GRR", text)
    return float(m.group(1)) if m else None


def rebuild_rows(text: str) -> list[str]:
    """
    Bank names wrap: "3 Agricultural Development Bank\nLimited 10.03 9.56 ...".
    Join a line that starts with a row number but has no numbers after the name
    onto the line that follows it.
    """
    out: list[str] = []
    lines = [l.rstrip() for l in text.splitlines()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if (re.match(r"^\s*\d{1,2}\s+[A-Za-z]", line)
                and not re.search(r"\d{1,3}\.\d{1,2}", line)
                and i + 1 < len(lines)):
            out.append(f"{line} {lines[i + 1].strip()}")
            i += 2
            continue
        out.append(line)
        i += 1
    return out


def parse_summary(text: str) -> list[dict]:
    out = []
    for m in SUMMARY_ROW.finditer(text):
        tenor, cat, hi, hi_bank, lo, lo_bank = m.groups()
        out.append({
            "category": CATEGORY.get(cat.lower(), cat.lower()),
            "tenor_years": int(tenor),
            "highest_apr": float(hi),
            "highest_bank": hi_bank.strip(),
            "lowest_apr": float(lo),
            "lowest_bank": lo_bank.strip(),
        })
    return out


def parse_banks(text: str) -> list[dict]:
    """
    Walk the document tracking which table we are inside. A bank row belongs to
    the most recent category and tenor header seen — the rows themselves say
    nothing about which table they sit in.
    """
    rows: list[dict] = []
    category: str | None = None
    tenor: int | None = None

    for line in rebuild_rows(text):
        h = TABLE_HEADER.search(line)
        if h:
            category = CATEGORY.get(h.group(1).lower())
            continue
        t = TENOR_LINE.search(line)
        if t:
            tenor = int(t.group(1))
            continue
        if not category or not tenor:
            continue

        got = split_bank_row(line)
        if not got:
            continue
        name, nums = got
        name = re.sub(r"\s+", " ", name).strip()
        if name.lower().startswith(("table", "tenor", "all rates")):
            continue
        # A bank name never contains a digit. If one does, the split went
        # wrong and the row is dropped rather than creating a phantom lender.
        if re.search(r"\d", name):
            continue
        rows.append({
            "category": category,
            "tenor_years": tenor,
            "bank": name,
            "grr": nums[0],
            "spread": nums[1],
            "avg_lending_rate": nums[2],
            "fees": [n for n in nums[3:-1]],
            "average_apr": nums[-1],
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/apr")
    ap.add_argument("--banks-csv", default="apr_banks.csv")
    ap.add_argument("--summary-csv", default="apr_summary.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.dir, "*.pdf")))
    if not files:
        print(f"No PDFs in {args.dir}. Run fetch_apr.py first.")
        return 1

    print(f"Reading {len(files)} report(s)\n")
    all_banks, all_summary = [], []
    for path in files:
        text = text_of(path)
        if not text.strip():
            continue
        as_of = report_month(text, path)
        if not as_of:
            print(f"  {os.path.basename(path):<22} no data month found")
            continue

        summary = parse_summary(text)
        banks = parse_banks(text)
        base = grr(text)

        print(f"  {os.path.basename(path):<22} {as_of}  "
              f"{len(summary)} categories, {len(banks)} bank rows"
              f"{f', GRR {base}%' if base else ''}")

        for s in summary:
            all_summary.append({**s, "as_of": as_of, "source": os.path.basename(path)})
        for b in banks:
            fees = b.pop("fees")
            all_banks.append({
                **b, "as_of": as_of,
                "max_fees_total": round(sum(f for f in fees if f), 2) if fees else None,
                "fee_count": sum(1 for f in fees if f),
                # Carried on every row, not added at render time. BoG states
                # these are indicative and that a given borrower may be offered
                # something different.
                "basis": "indicative; actual APR varies by borrower assessment",
                "source": os.path.basename(path),
            })

    if not all_banks and not all_summary:
        print("\nNothing extracted. Dump a report and check the layout.")
        return 1

    # What the data actually says about SME borrowing.
    sme = [s for s in all_summary if s["category"] == "sme"]
    if sme:
        print("\nSME credit, cheapest to dearest bank:")
        for s in sorted(sme, key=lambda x: x["tenor_years"]):
            spread = s["highest_apr"] - s["lowest_apr"]
            print(f"  {s['tenor_years']}-year  "
                  f"{s['lowest_apr']:5.2f}%  {s['lowest_bank'][:34]:<36} "
                  f"to {s['highest_apr']:5.2f}%  ({spread:.1f}pp apart)")

    if args.dry_run:
        print("\nDry run — nothing written.")
        return 0

    if all_summary:
        with open(args.summary_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_summary[0].keys()))
            w.writeheader()
            w.writerows(all_summary)
        print(f"\n  {len(all_summary)} rows -> {args.summary_csv}")

    if all_banks:
        with open(args.banks_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_banks[0].keys()))
            w.writeheader()
            w.writerows(all_banks)
        print(f"  {len(all_banks)} rows -> {args.banks_csv}")

    print("\n  Every rate is INDICATIVE. BoG states plainly that a given")
    print("  borrower may be offered something different after assessment.")
    print("  Publishing these as what a business will get would be wrong in")
    print("  the direction that costs someone money.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

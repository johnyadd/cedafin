"""
extract_gold_coin.py — prices, and the two things they hide.

WHAT IS ON EACH CIRCULAR
    1.00 oz  GH¢ 53,013.65
    0.50 oz  GH¢ 26,857.84
    0.25 oz  GH¢ 13,802.71
    LBMA PM price (previous day's close) = $ 4,568.95
    Bloomberg REGN USDGHS (previous day's close) = 11.2150

Bank of Ghana prints all five figures, which means two useful things can be
worked out that nobody publishes.

FIRST: THE PREMIUM OVER SPOT
An ounce of gold at $4,568.95 and GH¢11.2150 to the dollar is worth about
GH¢51,236. The coin sells for GH¢53,014. The difference is roughly 3.5% — what
a buyer pays for minting, guarantee and distribution. It is a real cost and it
is nowhere stated, because BoG publishes a price rather than a breakdown.

SECOND: THE SMALL-COIN PENALTY
Four quarter-ounce coins cost more than one full ounce:

    1 × 1.00 oz   GH¢53,014
    2 × 0.50 oz   GH¢53,716    (+GH¢702)
    4 × 0.25 oz   GH¢55,211    (+GH¢2,197)

The saver with least money pays most per ounce. That is the same pattern this
site found in fund minimums and bank lending, and it is invisible unless
somebody multiplies the small denominations out — which is precisely the
arithmetic a comparison site exists to do.

WHY THE FX RATE IS STORED, NOT DISCARDED
Between the November 2024 launch and July 2026, gold rose about 52% in dollars
while the coin rose about 6% in cedis. The entire difference was the cedi
strengthening from 15.75 to 11.54 against the dollar. Someone who bought gold
as a hedge received almost none of the move they were hedging for. Keeping the
cedi price without the rate that produced it would make that impossible to see.

Usage:
    python extract_gold_coin.py --dry-run
    python extract_gold_coin.py
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

# "FRIDAY, 28 AUGUST 2026" — the weekday is present but not needed.
DATE_RX = re.compile(r"(\d{1,2})\s+([A-Z]+)\s+(\d{4})", re.I)

# "1.00 oz GH¢ 53,013.65" — the cedi sign extracts inconsistently across
# readers, so anything non-numeric between the unit and the figure is allowed.
PRICE_RX = re.compile(
    r"(\d\.\d{2})\s*oz\s*[^\d]{0,12}([\d,]+\.\d{2})", re.I)

LBMA_RX = re.compile(r"LBMA[^=]*=\s*\$?\s*([\d,]+\.\d{2})", re.I)
FX_RX = re.compile(r"USDGHS[^=]*=\s*([\d.]+)", re.I)


def text_of(path: str) -> str:
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception as e:                                   # noqa: BLE001
        print(f"    unreadable: {type(e).__name__}: {e}")
        return ""


def num(s: str) -> float:
    return float(s.replace(",", ""))


def parse(path: str) -> dict | None:
    text = text_of(path)
    if not text.strip():
        return None

    m = DATE_RX.search(text)
    as_of = None
    if m:
        mon = MONTHS.get(m.group(2).lower())
        if mon:
            as_of = date(int(m.group(3)), mon, int(m.group(1))).isoformat()
    if not as_of:
        fm = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
        as_of = fm.group(1) if fm else None
    if not as_of:
        return None

    prices = {oz: num(v) for oz, v in PRICE_RX.findall(text)}
    if not prices:
        return None

    lm = LBMA_RX.search(text)
    fm = FX_RX.search(text)
    lbma = num(lm.group(1)) if lm else None
    fx = float(fm.group(1)) if fm else None

    row: dict = {"as_of": as_of, "lbma_usd_oz": lbma, "usd_ghs": fx,
                 "source": os.path.basename(path)}
    for oz in ("1.00", "0.50", "0.25"):
        row[f"ghs_{oz.replace('.', '_')}oz"] = prices.get(oz)

    # Spot value of one ounce in cedis, from the two figures BoG prints.
    spot_ghs = lbma * fx if (lbma and fx) else None
    row["spot_ghs_oz"] = round(spot_ghs, 2) if spot_ghs else None

    one = prices.get("1.00")
    row["premium_pct"] = (
        round((one / spot_ghs - 1) * 100, 2) if (one and spot_ghs) else None
    )

    # What the same ounce costs bought in smaller pieces.
    half, quarter = prices.get("0.50"), prices.get("0.25")
    row["ghs_per_oz_via_half"] = round(half * 2, 2) if half else None
    row["ghs_per_oz_via_quarter"] = round(quarter * 4, 2) if quarter else None
    row["small_coin_penalty_pct"] = (
        round((quarter * 4 / one - 1) * 100, 2) if (quarter and one) else None
    )
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/goldcoin")
    ap.add_argument("--out", default="gold_coin_prices.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.dir, "*.pdf")))
    if not files:
        print(f"No PDFs in {args.dir}. Run fetch_gold_coin.py first.")
        return 1

    print(f"Reading {len(files)} circular(s)\n")
    rows = []
    for p in files:
        r = parse(p)
        if not r:
            print(f"  {os.path.basename(p):<22} nothing extracted")
            continue
        rows.append(r)

    if not rows:
        print("Nothing extracted. Dump a circular and check the layout.")
        return 1

    rows.sort(key=lambda r: r["as_of"])
    first, last = rows[0], rows[-1]

    print(f"  {len(rows)} day(s), {first['as_of']} to {last['as_of']}\n")
    for r in rows[-5:]:
        print(f"  {r['as_of']}  1oz GH¢{r['ghs_1_00oz']:>10,.2f}   "
              f"LBMA ${r['lbma_usd_oz']:>8,.2f}   "
              f"USDGHS {r['usd_ghs']}   "
              f"premium {r['premium_pct']}%")

    prem = [r["premium_pct"] for r in rows if r["premium_pct"] is not None]
    pen = [r["small_coin_penalty_pct"] for r in rows
           if r["small_coin_penalty_pct"] is not None]

    if prem:
        print(f"\n  Premium over spot: {min(prem):.2f}% to {max(prem):.2f}% "
              f"(average {sum(prem)/len(prem):.2f}%)")
        print("  That is what the coin costs above the metal in it — minting,")
        print("  guarantee and distribution. BoG publishes a price, not this.")

    if pen and last.get("ghs_1_00oz") and last.get("ghs_per_oz_via_quarter"):
        gap = last["ghs_per_oz_via_quarter"] - last["ghs_1_00oz"]
        print(f"\n  Small-coin penalty: buying an ounce as four quarter-ounce")
        print(f"  coins costs {sum(pen)/len(pen):.2f}% more on average — "
              f"GH¢{gap:,.0f} more at the latest price.")
        print("  The saver with the least money pays the most per ounce.")

    # What actually happened to a cedi holder over the period covered.
    if (first.get("ghs_1_00oz") and last.get("ghs_1_00oz")
            and first.get("lbma_usd_oz") and last.get("lbma_usd_oz")):
        ghs_move = (last["ghs_1_00oz"] / first["ghs_1_00oz"] - 1) * 100
        usd_move = (last["lbma_usd_oz"] / first["lbma_usd_oz"] - 1) * 100
        print(f"\n  Over {first['as_of']} to {last['as_of']}:")
        print(f"    gold in dollars   {usd_move:+.1f}%")
        print(f"    the coin in cedis {ghs_move:+.1f}%")
        if first.get("usd_ghs") and last.get("usd_ghs"):
            print(f"    USD/GHS moved {first['usd_ghs']} -> {last['usd_ghs']}")
        print("  A Ghanaian buying gold as a hedge gets the dollar move minus")
        print("  whatever the cedi does. Showing one without the other would")
        print("  misrepresent what they actually earned.")

    if args.dry_run:
        print("\nDry run — nothing written.")
        return 0

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  {len(rows)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

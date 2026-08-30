"""
fetch_goldbod_price.py — what a Ghanaian miner is paid for gold.

WHAT THIS IS, AND WHAT IT IS NOT
GoldBod publishes an approved purchase price on its homepage each afternoon:

    Friday, 28th August 2026 @ 2:00 PM
    LBMA PM Price (per ounce)            USD 4,562.75
    Reference Rate for financing window  USD 1 = 11.1185
    Discount Rate                        0%
    Total Price Per Pound                GHS 12,118.00

This is the price licensed buyers pay artisanal miners, and licensees are
required to adhere to it. It is NOT a price an investor can buy at. Presenting
it as one would be badly wrong.

WHY IT BELONGS ON THE SITE ANYWAY
It is the floor of the chain. Bank of Ghana sells a one-ounce coin at about
3.5% above LBMA spot; GoldBod's approved price is what the metal costs at the
other end, before refining, minting, guarantee and distribution. Holding both
shows the whole markup from the person who dug it up to the person who saves
in it. Nobody publishes that comparison, and it is exactly the kind of thing
this site exists to put side by side.

THE DISCOUNT RATE IS THE FIGURE TO WATCH
It read 0% on 28 August. A discount is the margin GoldBod takes below world
spot when buying from miners, so a change in it is a change in what Ghanaian
miners receive for the same gold. That is a policy decision affecting hundreds
of thousands of livelihoods, published daily and, as far as I can tell,
tracked by no one.

"PER POUND" IS NOT AN OUNCE, AND THE CONVERSION IS NOT STATED
GoldBod quotes per pound. Which pound — troy, avoirdupois, or a local trading
unit — is not published on the page, and the arithmetic does not obviously fit
any of them. So the raw figure is stored and NO per-ounce conversion is
computed. Guessing a unit would produce a plausible number that is wrong, which
is worse than leaving a gap. Ask GoldBod; until then, the field stays empty.

Usage:
    python fetch_goldbod_price.py
    python fetch_goldbod_price.py --show
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import date

URL = "https://goldbod.gov.gh/"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*",
}

MONTHS = {m.lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}

# "Friday, 28th August 2026 @ 2:00 PM"
DATE_RX = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})", re.I)
LBMA_RX = re.compile(r"LBMA[^$]*?USD\s*([\d,]+\.\d{2})", re.I | re.S)
FX_RX = re.compile(r"USD\s*1\s*=\s*([\d.]+)", re.I)
DISCOUNT_RX = re.compile(r"Discount\s*Rate[^\d\-]{0,40}(-?[\d.]+)\s*%", re.I | re.S)
PRICE_RX = re.compile(
    r"Total\s*Price\s*Per\s*Pound[^\d]{0,40}([\d,]+\.\d{2})", re.I | re.S)


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ctx()) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:                                   # noqa: BLE001
        print(f"  {type(e).__name__}: {str(e)[:100]}")
        return ""


def strip_tags(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text.replace("&nbsp;", " "))


def num(s: str) -> float:
    return float(s.replace(",", ""))


def parse(text: str) -> dict | None:
    m = DATE_RX.search(text)
    as_of = None
    if m:
        mon = MONTHS.get(m.group(2).lower())
        if mon:
            as_of = date(int(m.group(3)), mon, int(m.group(1))).isoformat()

    lb = LBMA_RX.search(text)
    fx = FX_RX.search(text)
    di = DISCOUNT_RX.search(text)
    pr = PRICE_RX.search(text)

    if not pr:
        return None
    return {
        "as_of": as_of or date.today().isoformat(),
        "lbma_usd_oz": num(lb.group(1)) if lb else None,
        "usd_ghs": float(fx.group(1)) if fx else None,
        "discount_pct": float(di.group(1)) if di else None,
        "ghs_per_pound": num(pr.group(1)),
        # Deliberately empty. GoldBod does not publish which pound it means,
        # and a guessed conversion would look authoritative and be wrong.
        "ghs_per_oz": None,
        "source": URL,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="goldbod_prices.csv")
    ap.add_argument("--show", action="store_true",
                    help="Print today's figures without writing.")
    args = ap.parse_args()

    html = fetch(URL)
    if not html:
        print("Could not reach goldbod.gov.gh")
        return 1

    row = parse(strip_tags(html))
    if not row:
        print("Price block not found. The homepage layout may have changed —")
        print("open https://goldbod.gov.gh/ and check the panel is still there.")
        return 1

    print(f"  {row['as_of']}")
    print(f"    LBMA PM             USD {row['lbma_usd_oz']:,.2f} /oz"
          if row["lbma_usd_oz"] else "    LBMA PM             —")
    print(f"    Reference rate      USD 1 = {row['usd_ghs']}"
          if row["usd_ghs"] else "    Reference rate      —")
    print(f"    Discount rate       {row['discount_pct']}%"
          if row["discount_pct"] is not None else "    Discount rate       —")
    print(f"    Approved price      GHS {row['ghs_per_pound']:,.2f} per pound")

    if row["lbma_usd_oz"] and row["usd_ghs"]:
        spot_oz = row["lbma_usd_oz"] * row["usd_ghs"]
        print(f"\n    An ounce at world spot, in cedis: GHS {spot_oz:,.2f}")
        print("    GoldBod quotes per POUND and does not publish the")
        print("    conversion, so no per-ounce figure is derived here. Two")
        print("    numbers that cannot be compared are left uncompared.")

    if args.show:
        print("\nShow only — nothing written.")
        return 0

    # Append, keeping one row per day. The page updates each afternoon, so
    # running this daily builds the series that makes the discount rate
    # meaningful — one reading says nothing about whether it moves.
    seen: set[str] = set()
    rows: list[dict] = []
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                rows.append(r)
                seen.add(r["as_of"])

    if row["as_of"] in seen:
        print(f"\n  {row['as_of']} already recorded — nothing added.")
        return 0

    rows.append(row)
    rows.sort(key=lambda r: r["as_of"])
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n  {len(rows)} day(s) recorded -> {args.out}")
    print("\n  This is what a MINER is paid, not what an investor pays. Bank")
    print("  of Ghana sells a one-ounce coin at about 3.5% above world spot;")
    print("  this is the other end of the same chain. Showing both is the")
    print("  only way to see the whole markup.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

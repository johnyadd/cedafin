"""
fetch_gse_reports.py — the Ghana Stock Exchange's own monthly market reports.

WHY THE EXCHANGE'S OWN PDF AND NOT A LIVE FEED
Five sites publish GSE prices free and faster than we ever could: Mansa
refreshes every 30 minutes, GhanaStockMarket runs a portfolio tracker and a
daily newsletter, and afx.kwayisi, mystocks.africa and africanfinancials all
carry the same board. Competing on price data would be pointless and, worse,
it would mean publishing figures derived from someone else's feed — which
breaks the rule every other page on this site follows: every number traces to a
document its issuer published.

The exchange publishes its own monthly report. Monthly is the same cadence as
the fund factsheets already loaded, and for comparing what things cost it is
entirely sufficient. What it buys is provenance.

WHAT IS IN IT
All listed equities with market capitalisation, shares outstanding and dividend
yield, plus index history back to 1990. Two things follow.

  NEWGOLD ETF (GLD). The one gold product on the exchange, roughly 1/100 oz of
  bullion per unit at about GH¢495. Set against the Ghana Gold Coin at
  GH¢13,803 for the cheapest denomination, it is twenty-eight times cheaper to
  start — which for most Ghanaian savers is the difference between possible and
  not. It is also Sharia-compliant, and as far as this project has established
  the only such product listed in Ghana.

  DIVIDEND YIELDS. A yield is comparable with a fund's return and a Treasury
  bill's rate in a way a share price is not. It is the number that lets equities
  sit on the same page as everything else here.

WHAT IT DOES NOT SOLVE
What a Ghanaian broker charges to buy any of it. Nobody publishes that —
mystocks.africa quotes 0.75% for international buyers and the licensed dealing
members in Accra publish nothing. That is the same gap this site found in fund
fees, deposit rates and SME lending, and no PDF will close it.

URL PATTERN
    .../wp-content/uploads/2026/05/GSE-Equities-Market-Report-April-2026-compressed.pdf

Verified against one real report. The upload folder is the month AFTER the data
month, so both are tried. BoG changed filename conventions twice this year, so
a listing-page fallback is built in rather than added after it breaks.

Usage:
    python fetch_gse_reports.py --probe
    python fetch_gse_reports.py --months 18
"""

from __future__ import annotations

import argparse
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

BASE = "https://gse.com.gh/wp-content/uploads"
LISTING = "https://gse.com.gh/trading-and-data/"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "application/pdf,text/html,*/*",
}

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 45) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return getattr(r, "status", 200), r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:                                        # noqa: BLE001
        return 0, b""


def is_pdf(b: bytes) -> bool:
    return b[:5] == b"%PDF-"


def candidates(year: int, month: int) -> list[str]:
    """
    Known-good, from a real report:
        .../2026/05/GSE-Equities-Market-Report-April-2026-compressed.pdf

    Note the folder is the month AFTER the data month — April's report was
    uploaded in May. Same publication lag as Bank of Ghana's APR reports.
    """
    name = MONTHS[month - 1]
    forms = [
        f"GSE-Equities-Market-Report-{name}-{year}-compressed.pdf",
        f"GSE-Equities-Market-Report-{name}-{year}.pdf",
        f"GSE-Equities-Market-Report-{name}{year}-compressed.pdf",
        f"GSE-Equities-Market-Report-{name}-{year}-1.pdf",
        f"GSE-Market-Report-{name}-{year}.pdf",
        f"Equities-Market-Report-{name}-{year}.pdf",
    ]
    folders = []
    for lag in (1, 2, 0, 3):
        m = month + lag
        y = year + (m > 12)
        m = m - 12 if m > 12 else m
        folders.append(f"{y}/{m:02d}")

    out: list[str] = []
    for folder in folders:
        for form in forms:
            u = f"{BASE}/{folder}/{form}"
            if u not in out:
                out.append(u)
    return out


def url_from_listing(year: int, month: int) -> str | None:
    """
    Read the trading-and-data page for a link naming this month. Slower than a
    guess and immune to a convention change, which has caught two fetchers on
    this project already.
    """
    status, blob = fetch(LISTING)
    if status != 200 or not blob:
        return None
    html = blob.decode("utf-8", errors="replace")
    name = MONTHS[month - 1]
    for m in re.finditer(
        r'href=["\'](https?://[^"\']*?/wp-content/uploads/[^"\']*?\.pdf)', html, re.I
    ):
        u = m.group(1)
        if name.lower() in u.lower() and str(year) in u:
            return u
    return None


def get_month(year: int, month: int, delay: float) -> tuple[str, bytes] | None:
    for url in candidates(year, month):
        status, blob = fetch(url)
        if status == 200 and is_pdf(blob):
            return url, blob
        time.sleep(delay)

    real = url_from_listing(year, month)
    if real:
        status, blob = fetch(real)
        if status == 200 and is_pdf(blob):
            return real, blob
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-year", type=int, default=2026)
    ap.add_argument("--from-month", type=int, default=7,
                    help="Most recent DATA month to try. Reports lag by a month.")
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--out", default="data/gse")
    ap.add_argument("--delay", type=float, default=0.6)
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    y, m = args.from_year, args.from_month

    if args.probe:
        print("Probing four recent months\n")
        for _ in range(4):
            print(f"  {MONTHS[m - 1]} {y}")
            got = get_month(y, m, args.delay)
            if got:
                url, blob = got
                print(f"    HIT  {len(blob):>9,} bytes")
                print(f"    {url}")
            else:
                print("    miss")
                for u in candidates(y, m)[:2]:
                    print(f"      tried {u}")
            m -= 1
            if m < 1:
                m, y = 12, y - 1
        print(f"\nIf all missed, open {LISTING} in a browser, right-click a")
        print("report link and paste the URL. Guessing filenames has cost more")
        print("rounds on this project than reading a page ever has.")
        return 0

    os.makedirs(args.out, exist_ok=True)
    ok = miss = 0
    for _ in range(args.months):
        path = os.path.join(args.out, f"gse-{y}-{m:02d}.pdf")
        if os.path.exists(path):
            print(f"  {MONTHS[m - 1]:<10} {y}  already held")
        else:
            got = get_month(y, m, args.delay)
            if got:
                url, blob = got
                with open(path, "wb") as f:
                    f.write(blob)
                ok += 1
                print(f"  {MONTHS[m - 1]:<10} {y}  {len(blob):>9,} bytes")
            else:
                miss += 1
                print(f"  {MONTHS[m - 1]:<10} {y}  not found")
        m -= 1
        if m < 1:
            m, y = 12, y - 1
        time.sleep(args.delay)

    print(f"\n  {ok} downloaded, {miss} missing -> {args.out}")
    if ok:
        print("\n  These are the EXCHANGE's own reports, not a derived feed.")
        print("  Five sites publish GSE prices faster; none of them is the")
        print("  issuer. The point of using these is that every figure traces")
        print("  to a document the exchange published, which is the standard")
        print("  every other page on this site is held to.")
        print("\n  Still missing, and no PDF will fix it: what a Ghanaian")
        print("  broker charges to trade any of this. The licensed dealing")
        print("  members publish nothing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

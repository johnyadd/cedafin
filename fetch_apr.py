"""
fetch_apr.py — Bank of Ghana's monthly APR report for every licensed bank.

WHY THIS IS THE BEST SOURCE IN THE PROJECT
The investment side took a day to establish: 83 managers, 31 dead domains,
five funds with usable history, and a per-provider adapter for each. The
borrowing side has ONE regulatory publication, monthly, covering every
licensed bank, broken down by household / SME / corporate and by tenor — and
Bank of Ghana publishes it expressly so borrowers can compare.

May 2026, to show what is in it:
    average APR, all categories      17.64%
    highest among commercial banks   39.27%
    lowest 5-year household          5.03%   (OmniBSIC)
    lowest 1-year corporate           7.62%  (Absa)
    Ghana Reference Rate             ~10%

A spread above 28 percentage points in some categories — a borrower paying
nearly four times another for the same product, at the same time, in the same
market. That gap is the entire argument for a comparison site, and it comes
from the regulator rather than from us.

WHAT IT COVERS, AND WHAT IT DOES NOT
All ~23 licensed BANKS. It does NOT cover microfinance institutions, savings
and loans companies, or fintech lenders (Fido, Carbon and the rest). Those
matter: BoG's own capital rules make small loans uneconomic for banks, so the
SMEs least able to get bank credit are exactly the ones borrowing from
institutions absent from this report. Bank coverage is a strong start and a
partial picture, and any page built on it must say so.

BoG serves no robots.txt — verified, returns 404 — so no crawl preference has
been expressed. Standard politeness applies: truthful user agent, delay
between requests, cache, and monthly rather than constant.

Usage:
    python fetch_apr.py --probe
    python fetch_apr.py --months 18
"""

from __future__ import annotations

import argparse
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import date

BASE = "https://www.bog.gov.gh/wp-content/uploads"
# APR reports are published as NOTICES, not in any downloads section — which
# is why guessing folders found nothing. The notice URL is fully predictable:
#   /notice/annual-percentage-rates-apr-of-banks-as-at-may-2026/
# and it carries the real PDF link. Reading that page beats guessing the
# filename, because the filename convention has already changed once:
#   APR-For-June-2025.pdf      (2025)
#   MAY-APR-2026.pdf           (2026)  month first, then APR, then year
NOTICE = ("https://www.bog.gov.gh/notice/"
          "annual-percentage-rates-apr-of-banks-as-at-{month}-{year}/")
LISTING = "https://www.bog.gov.gh/?s=APR"

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


def fetch(url: str, timeout: int = 40) -> tuple[int, bytes]:
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
    Known-good shape, from a real URL:
        .../2025/08/APR-For-June-2025.pdf

    Note the folder is the month of PUBLICATION, not of the data — June's
    report was uploaded in August. That lag is why several folders are tried
    rather than assuming the data month.
    """
    name = MONTHS[month - 1]
    up = name.upper()
    forms = [
        f"APRs-For-{name}-{year}.pdf",
        f"{up}-APR-{year}.pdf",
        f"APR-For-{name}-{year}.pdf",    # 2025 convention
        f"{name}-APR-{year}.pdf",
        f"APR-{up}-{year}.pdf",
        f"{up}-APR-{year}-1.pdf",
        f"APR-For-{name}-{year}-1.pdf",
    ]
    folders = []
    # Reports appear one to three months after the data month.
    for lag in (2, 1, 3, 0):
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


def url_from_notice(year: int, month: int) -> str | None:
    """
    Read the month's notice page for the real PDF link.

    Slower than a direct guess and immune to convention changes, which have
    already caught this fetcher once. Every guess-first attempt on this project
    has cost rounds; reading the page has cost none.
    """
    url = NOTICE.format(month=MONTHS[month - 1].lower(), year=year)
    status, blob = fetch(url)
    if status != 200 or not blob:
        return None
    html = blob.decode("utf-8", errors="replace")
    m = re.search(r'href=["\'](https?://[^"\']*?/wp-content/uploads/[^"\']*?\.pdf)',
                  html, re.I)
    return m.group(1) if m else None


def get_month(year: int, month: int, delay: float) -> tuple[str, bytes] | None:
    for url in candidates(year, month):
        status, blob = fetch(url)
        if status == 200 and is_pdf(blob):
            return url, blob
        time.sleep(delay)

    real = url_from_notice(year, month)
    if real:
        status, blob = fetch(real)
        if status == 200 and is_pdf(blob):
            return real, blob
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-year", type=int, default=2026)
    ap.add_argument("--from-month", type=int, default=6,
                    help="Most recent data month to try. Reports lag by 1-3 "
                         "months, so the newest available is rarely this one.")
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--out", default="data/apr")
    ap.add_argument("--delay", type=float, default=0.7)
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    y, m = args.from_year, args.from_month
    if args.probe:
        print("Probing three recent months\n")
        for _ in range(3):
            print(f"  {MONTHS[m - 1]} {y}")
            got = get_month(y, m, args.delay)
            if got:
                url, blob = got
                print(f"    HIT  {len(blob):>8,} bytes")
                print(f"    {url}")
            else:
                print("    miss")
                for u in candidates(y, m)[:3]:
                    print(f"      tried {u}")
            m -= 1
            if m < 1:
                m, y = 12, y - 1
        print(f"\nIf all missed, search {LISTING} in a browser, open a notice")
        print("and paste the PDF link. Guessing filenames has cost more rounds")
        print("on this project than reading a page ever has.")
        return 0

    os.makedirs(args.out, exist_ok=True)
    ok = miss = 0
    for _ in range(args.months):
        path = os.path.join(args.out, f"apr-{y}-{m:02d}.pdf")
        if os.path.exists(path):
            print(f"  {MONTHS[m - 1]} {y}  already held")
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
        print("\n  These cover LICENSED BANKS ONLY — around 23 of them.")
        print("  Microfinance, savings and loans, and fintech lenders (Fido,")
        print("  Carbon) are NOT in this report, and they are where SMEs")
        print("  refused by banks actually borrow. Any page built on this")
        print("  data has to say what it leaves out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

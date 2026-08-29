"""
fetch_gold_coin.py — Bank of Ghana's daily Ghana Gold Coin prices.

WHAT THE GHANA GOLD COIN IS
A gold investment product issued and guaranteed by Bank of Ghana, launched
November 2024. Three denominations — 1 oz, ½ oz, ¼ oz — at 99.99% purity from
responsibly mined Ghanaian gold. Not legal tender. Bought through a commercial
bank rather than from BoG directly, paid by transfer or mobile money.

BoG publishes a price circular every working day by 9am, derived from the
previous day's LBMA PM gold price and the Bloomberg USD/GHS mid-rate.

WHY THIS SERIES MATTERS MORE THAN THE PRICE

    Nov 2024 (launch)   1 oz = GH¢45,020     LBMA $2,635
    Apr 2026            1 oz = GH¢54,251     LBMA $4,774
    Jul 2026            1 oz = GH¢47,779     LBMA $3,994

Gold rose about 51% in dollars over that period. The coin rose about 6% in
cedis. The difference is the exchange rate: the cedi went from 15.75 to 11.54
to the dollar, and a strengthening currency ate almost the entire dollar gain.

A Ghanaian who bought gold to hedge got very little of what they were hedging
for, and nobody is showing them that. Holding the LBMA price and the FX rate
alongside the cedi price — all three are printed on the same circular — is what
makes that visible. Storing only the cedi price would hide the reason it moved.

TAX, WHICH IS GENUINELY DIFFERENT HERE
The coin is exempt from VAT and, under current Ghanaian law, capital gains on
it are not taxed. Treasury bill interest carries withholding tax. That is a
real distinction between two products a saver might weigh against each other,
and it belongs beside the prices rather than in a footnote.

URL PATTERN, AND THE FALLBACK
    .../wp-content/uploads/2026/04/PRICING-13.04.2026.pdf

Verified against three real circulars. But BoG has changed filename conventions
twice this year on other publications, so each date also has a notice page at a
predictable address which carries the real link:

    /notice/ghana-gold-coin-pricing-13-april-2026/

Guessing filenames has cost more time on this project than reading a page ever
has, so the fallback is built in from the start rather than added after it
breaks.

Usage:
    python fetch_gold_coin.py --probe
    python fetch_gold_coin.py --days 90
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
from datetime import date, timedelta

BASE = "https://www.bog.gov.gh/wp-content/uploads"
NOTICE = "https://www.bog.gov.gh/notice/ghana-gold-coin-pricing-{d}-{month}-{y}/"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "application/pdf,text/html,*/*",
}

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

# The coin launched on this date; nothing exists before it.
LAUNCH = date(2024, 11, 26)


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 30) -> tuple[int, bytes]:
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


def candidates(d: date) -> list[str]:
    """
    Known-good: .../2026/04/PRICING-13.04.2026.pdf

    The upload folder is the month of publication, which for a same-day
    circular is the same month. A previous-month folder is tried second for
    circulars published at a month boundary.
    """
    dd, mm, yyyy = f"{d.day:02d}", f"{d.month:02d}", d.year
    names = [
        f"PRICING-{dd}.{mm}.{yyyy}.pdf",
        f"PRICING-{dd}-{mm}-{yyyy}.pdf",
        f"PRICING-{dd}.{mm}.{yyyy}-1.pdf",
        f"Pricing-{dd}.{mm}.{yyyy}.pdf",
        f"GGC-PRICING-{dd}.{mm}.{yyyy}.pdf",
    ]
    prev = d.replace(day=1) - timedelta(days=1)
    folders = [f"{yyyy}/{mm}", f"{prev.year}/{prev.month:02d}"]

    out: list[str] = []
    for folder in folders:
        for n in names:
            u = f"{BASE}/{folder}/{n}"
            if u not in out:
                out.append(u)
    return out


def url_from_notice(d: date) -> str | None:
    """Read the day's notice page for the real PDF link."""
    url = NOTICE.format(d=d.day, month=MONTHS[d.month - 1].lower(), y=d.year)
    status, blob = fetch(url)
    if status != 200 or not blob:
        return None
    html = blob.decode("utf-8", errors="replace")
    m = re.search(r'href=["\'](https?://[^"\']*?/wp-content/uploads/[^"\']*?\.pdf)',
                  html, re.I)
    return m.group(1) if m else None


def get_day(d: date, delay: float) -> tuple[str, bytes] | None:
    for url in candidates(d):
        status, blob = fetch(url)
        if status == 200 and is_pdf(blob):
            return url, blob
        time.sleep(delay)

    real = url_from_notice(d)
    if real:
        status, blob = fetch(real)
        if status == 200 and is_pdf(blob):
            return real, blob
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30,
                    help="How many days back from --from to walk.")
    ap.add_argument("--from", dest="start", default=None,
                    help="YYYY-MM-DD. Defaults to today.")
    ap.add_argument("--out", default="data/goldcoin")
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    start = date.fromisoformat(args.start) if args.start else date.today()

    if args.probe:
        print("Probing five recent working days\n")
        d, tried = start, 0
        while tried < 5:
            if d.weekday() >= 5:          # circulars are working days only
                d -= timedelta(days=1)
                continue
            tried += 1
            print(f"  {d.isoformat()}")
            got = get_day(d, args.delay)
            if got:
                url, blob = got
                print(f"    HIT  {len(blob):>7,} bytes")
                print(f"    {url}")
            else:
                print("    miss")
                for u in candidates(d)[:2]:
                    print(f"      tried {u}")
            d -= timedelta(days=1)
        print("\nIf all missed, search https://www.bog.gov.gh/?s=gold+coin+pricing")
        print("and paste a real PDF link rather than letting me guess again.")
        return 0

    os.makedirs(args.out, exist_ok=True)
    ok = miss = skipped = 0
    d = start
    for _ in range(args.days):
        if d < LAUNCH:
            print(f"  {d.isoformat()}  before launch — stopping")
            break
        if d.weekday() >= 5:
            d -= timedelta(days=1)
            continue

        path = os.path.join(args.out, f"ggc-{d.isoformat()}.pdf")
        if os.path.exists(path):
            skipped += 1
        else:
            got = get_day(d, args.delay)
            if got:
                url, blob = got
                with open(path, "wb") as f:
                    f.write(blob)
                ok += 1
                print(f"  {d.isoformat()}  {len(blob):>7,} bytes")
            else:
                miss += 1
        d -= timedelta(days=1)
        time.sleep(args.delay)

    print(f"\n  {ok} downloaded, {miss} missing, {skipped} already held "
          f"-> {args.out}")
    if ok:
        print("\n  Each circular carries THREE figures that matter together:")
        print("  the cedi price, the LBMA dollar price it derives from, and the")
        print("  USD/GHS rate used. Keep all three — the cedi price alone hides")
        print("  why it moved, and between Nov 2024 and Jul 2026 the reason was")
        print("  almost entirely the exchange rate rather than gold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

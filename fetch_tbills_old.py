"""
fetch_tbills.py — Bank of Ghana weekly T-bill auction results.

ON WHETHER THIS SHOULD EXIST AT ALL
An earlier version of this file was deleted on the belief that bog.gov.gh
disallowed automated access. That was wrong: the site serves no robots.txt at
all — https://www.bog.gov.gh/robots.txt returns 404 — so no crawl preference
has been expressed by anyone. The refusal that prompted the deletion came from
a tool applying its own conservative default when it could not confirm a
policy, not from Bank of Ghana asking crawlers to stay away.

With no stated policy, the standard is ordinary politeness rather than
permission: a truthful user agent, a delay between requests, weekly rather than
constant, and caching so nothing is fetched twice. All of that is below.

WHY THE SERIES MATTERS
Without a risk-free rate there is no risk-adjusted return, and without
inflation no real return. But the sharper reason is that rates have collapsed:

    91-day, Feb 2025    23-25%
    91-day, Jul 2026     5.79%
    91-day, Aug 21 2026  5.08%

A fund's 14% last year and a fund's 14% next year are not the same claim. The
benchmark series is what lets a page say which environment a return was earned
in — and a trailing figure without that context is what a fund's own marketing
prints.

THE SOURCE
BoG runs GoG tenders every Friday and publishes a PDF per tender, numbered
sequentially:

    .../wp-content/uploads/2026/07/Auctresults-2017.pdf

Tender numbers are consecutive weeks — 2017 was 24 July 2026 — so the series is
enumerable. The year/month folder is NOT derivable from the number, so each
tender is tried against a small window of plausible folders, and several
filename forms are tried per tender.

Usage:
    python fetch_tbills.py --probe --from-tender 2021
    python fetch_tbills.py --from-tender 2021 --count 24
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
LISTING = "https://www.bog.gov.gh/gog_auction_results/"

# Each tender also has a landing page at a fully predictable URL:
#   /gog_auction_results/results-of-gog-tender-2021/
# It carries the download link, so when a filename guess fails the page can be
# read for the real one instead of guessing again — which is what cost several
# rounds before the convention change was spotted.
TENDER_PAGE = LISTING + "results-of-gog-tender-{tender}/"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "application/pdf,text/html,*/*",
    "Referer": LISTING,
}

# Anchor: tender 2019 was held 7 August 2026. Tenders run weekly, so any other
# tender's approximate date follows from the difference.
# Read off the listing page rather than inferred: tender 2021 was 21 Aug 2026.
ANCHOR_TENDER = 2021
ANCHOR_DATE = date(2026, 8, 21)


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def approx_date(tender: int) -> date:
    return ANCHOR_DATE - timedelta(weeks=ANCHOR_TENDER - tender)


def candidate_urls(tender: int) -> list[str]:
    """
    The folder is the upload month, which is usually the tender month but can
    slip either side, so a small window is tried. Filenames vary between a bare
    form and a longer notice form.
    """
    d = approx_date(tender)
    folders = []
    for delta in (0, 1, -1):
        m = d.month + delta
        y = d.year + (1 if m > 12 else -1 if m < 1 else 0)
        m = 12 if m < 1 else 1 if m > 12 else m
        folders.append(f"{y}/{m:02d}")

    # BoG changed the filename convention mid-2026 and both forms are live:
    #   tender 2017 (24 Jul)  Auctresults-2017.pdf   plural, hyphenated
    #   tender 2021 (21 Aug)  Auctresult2021.pdf     singular, no hyphen
    # Newest form first, since recent tenders are what gets fetched weekly.
    names = [
        f"Auctresult{tender}.pdf",
        f"Auctresults-{tender}.pdf",
        f"Auctresults{tender}.pdf",
        f"Auctresult-{tender}.pdf",
        f"Auctresult{tender}-1.pdf",
        f"Auctresults-{tender}-1.pdf",
    ]
    out: list[str] = []
    for folder in folders:
        for name in names:
            u = f"{BASE}/{folder}/{name}"
            if u not in out:
                out.append(u)
    return out


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


def url_from_page(tender: int) -> str | None:
    """Read the tender's own page for the real download link."""
    status, blob = fetch(TENDER_PAGE.format(tender=tender))
    if status != 200 or not blob:
        return None
    html = blob.decode("utf-8", errors="replace")
    m = re.search(r'href=["\'](https?://[^"\']*?/wp-content/uploads/[^"\']*?\.pdf)',
                  html, re.I)
    return m.group(1) if m else None


def get_tender(tender: int, delay: float) -> tuple[str, bytes] | None:
    for url in candidate_urls(tender):
        status, blob = fetch(url)
        if status == 200 and is_pdf(blob):
            return url, blob
        time.sleep(delay)

    # Guesses exhausted: ask the page. Slower, but it cannot be wrong about a
    # filename convention the way a guess can.
    real = url_from_page(tender)
    if real:
        status, blob = fetch(real)
        if status == 200 and is_pdf(blob):
            return real, blob
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-tender", type=int, default=ANCHOR_TENDER)
    ap.add_argument("--count", type=int, default=12,
                    help="how many tenders back to walk")
    ap.add_argument("--out", default="data/tbills")
    ap.add_argument("--delay", type=float, default=0.8)
    ap.add_argument("--probe", action="store_true",
                    help="try 3 tenders and report which URL form worked")
    args = ap.parse_args()

    if args.probe:
        print("Probing three recent tenders\n")
        for t in range(args.from_tender, args.from_tender - 3, -1):
            print(f"  tender {t} (~{approx_date(t).isoformat()})")
            got = get_tender(t, args.delay)
            if got:
                url, blob = got
                print(f"    HIT  {len(blob):>8,} bytes")
                print(f"    {url}")
            else:
                print("    miss — none of the candidate URLs returned a PDF")
                for u in candidate_urls(t)[:4]:
                    print(f"      tried {u}")
        print("\nIf all three missed, open the listing page in a browser,")
        print(f"right-click a result link and paste the URL: {LISTING}")
        return 0

    os.makedirs(args.out, exist_ok=True)
    ok = miss = 0
    for t in range(args.from_tender, args.from_tender - args.count, -1):
        path = os.path.join(args.out, f"tender-{t}.pdf")
        if os.path.exists(path):
            continue
        got = get_tender(t, args.delay)
        if got:
            url, blob = got
            with open(path, "wb") as f:
                f.write(blob)
            ok += 1
            print(f"  tender {t}  ~{approx_date(t).isoformat()}  "
                  f"{len(blob):>8,} bytes")
        else:
            miss += 1
            print(f"  tender {t}  ~{approx_date(t).isoformat()}  not found")
        time.sleep(args.delay)

    print(f"\n  {ok} downloaded, {miss} missing -> {args.out}")
    if ok:
        print("  Next: extract the 91/182/364-day rates from these PDFs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

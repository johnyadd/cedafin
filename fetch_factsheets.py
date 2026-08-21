"""
fetch_factsheets.py — pull monthly factsheet back-issues by URL pattern.

WHY THIS EXISTS
The SIMS factsheet listing is JavaScript-rendered, so a plain fetch sees the
filter controls and no file list. But the download URL of any single factsheet
reveals the naming convention:

  /static_file/Ghana SIMS/Downloadable files/Monthly Facts Sheets/
      PDIF Fact Sheets/PDIF Fact Sheet - July 2026.pdf

Once the convention is known, every back-issue is addressable. That turns
"12 months of history" from a blocker into a download loop — the thing that
clears GATES.MIN_HISTORY_MONTHS in scoring-config.ts.

The site's own year filter offers 2017 through 2026, so the archive is deep.

POLITENESS: one request at a time with a delay. This is a research crawl of
public documents, not a scrape of anything gated. Keep the delay.

Usage:
  # confirm the known-good pattern first
  python fetch_factsheets.py --folder "PDIF Fact Sheets" --prefix "PDIF Fact Sheet - " --months 24

  # then whatever convention the retail funds use
  python fetch_factsheets.py --folder "SCT Fact Sheets" --prefix "SCT Fact Sheet - " --months 36

  # probe several guesses cheaply before committing to a long run
  python fetch_factsheets.py --probe --folder "..." --prefix "..."
"""

from __future__ import annotations

import argparse
import http.cookiejar
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

BASE = "https://www.sims.com.gh"
ROOT = "/static_file/Ghana SIMS/Downloadable files/Monthly Facts Sheets"

LISTING = (BASE + "/ghanasims/management-investment-services/about-us/"
                  "monthly-fact-sheets")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,application/pdf,*/*;q=0.8"),
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": LISTING,
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

# A bare request with no cookies gets a Cloudflare challenge page — served with
# status 200, which is why the %PDF- magic-byte check matters. Visiting the
# listing page first picks up the session cookies a browser would already hold.
_JAR = http.cookiejar.CookieJar()
_OPENER: urllib.request.OpenerDirector | None = None


def opener() -> urllib.request.OpenerDirector:
    global _OPENER
    if _OPENER is None:
        _OPENER = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(_JAR),
            urllib.request.HTTPSHandler(context=_ctx()),
        )
    return _OPENER


def warm_session() -> bool:
    """Visit the listing page to collect cookies before requesting PDFs."""
    req = urllib.request.Request(LISTING, headers=HEADERS)
    try:
        with opener().open(req, timeout=45) as r:
            r.read(50_000)
        print(f"  session warmed, {len(_JAR)} cookie(s)\n")
        return True
    except Exception as e:                                   # noqa: BLE001
        print(f"  could not warm session: {type(e).__name__}: {e}\n")
        return False

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def build_url(folder: str, prefix: str, when: date, suffix: str = "",
              year_dir: bool = True) -> str:
    """
    Real structure, read off an actual download URL:

      /Monthly Facts Sheets/<YEAR>/<FUND> Fact Sheets/<FUND> Fact Sheet - <Month> <Year>.pdf

    The <YEAR> directory is easy to miss and its absence produces a soft 404 —
    an HTML error page served with status 200. Hence the %PDF- magic-byte check.
    It also explains the year filter on the listing page: the archive is stored
    by year, 2017 through 2026.

    Path segments are encoded but '/' preserved, so spaces become %20.
    """
    name = f"{prefix}{MONTHS[when.month - 1]} {when.year}{suffix}.pdf"
    parts = [ROOT]
    if year_dir:
        parts.append(str(when.year))
    if folder:                      # empty folder = files sit in the year dir
        parts.append(folder)
    parts.append(name)
    return BASE + urllib.parse.quote("/".join(parts), safe="/")


# The layout CHANGED between years, confirmed against real links:
#   2025:  /Monthly Facts Sheets/2025/Stanbic Cash Trust Fact Sheet - April 2025.pdf
#   2026:  /Monthly Facts Sheets/2026/PDIF Fact Sheets/PDIF Fact Sheet - July 2026.pdf
# So 2025 has NO fund subfolder and 2026 does. Rather than pick one, try both
# per month and take whichever returns a real PDF. This is also a warning for
# the production ingester: a convention that changed once will change again,
# which is why every fetch snapshots raw bytes and why a soft 404 must never
# be mistaken for a hit.
def candidate_urls(folder: str, prefix: str, when: date, suffix: str) -> list[str]:
    seen: list[str] = []
    for yd in (True, False):
        for fld in ([folder, ""] if folder else [""]):
            u = build_url(fld, prefix, when, suffix, yd)
            if u not in seen:
                seen.append(u)
    return seen


def fetch_month(folder: str, prefix: str, when: date, suffix: str,
                delay: float) -> tuple[str, int, bytes]:
    """Try each layout; first real PDF wins. Returns (url, status, blob)."""
    last: tuple[str, int, bytes] = ("", 0, b"")
    for url in candidate_urls(folder, prefix, when, suffix):
        status, blob = try_fetch(url)
        if status == 200 and is_pdf(blob):
            return url, status, blob
        last = (url, status, blob)
        time.sleep(delay)
    return last


def try_fetch(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with opener().open(req, timeout=45) as r:
            return getattr(r, "status", 200), r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:                                        # noqa: BLE001
        return 0, b""


def describe_body(blob: bytes) -> str:
    """When a 200 is not a PDF, say what it actually was."""
    head = blob[:2000].decode("utf-8", errors="replace").lower()
    if "just a moment" in head or "cf-browser-verification" in head or "cdn-cgi/challenge" in head:
        return "Cloudflare challenge page"
    if "not found" in head or "404" in head:
        return "soft 404 (HTML error page served with status 200)"
    if "<html" in head:
        return "an HTML page, not a PDF"
    return f"{len(blob)} bytes, starting {blob[:16]!r}"


def month_back(d: date, n: int) -> date:
    total = (d.year * 12 + d.month - 1) - n
    return date(total // 12, total % 12 + 1, 1)


def is_pdf(blob: bytes) -> bool:
    """A 200 that returns an HTML error page is a miss, not a hit."""
    return blob[:5] == b"%PDF-"


def run(folder: str, prefix: str, months: int, out_dir: str,
        start: date, delay: float, suffix: str, year_dir: bool = True) -> int:
    os.makedirs(out_dir, exist_ok=True)
    warm_session()
    hits = misses = 0
    first_hit = last_hit = None

    for i in range(months):
        when = month_back(start, i)
        url, status, blob = fetch_month(folder, prefix, when, suffix, 0.4)
        label = f"{MONTHS[when.month - 1][:3]} {when.year}"

        if status == 200 and is_pdf(blob):
            path = os.path.join(out_dir,
                                f"{prefix}{when.year}-{when.month:02d}.pdf"
                                .replace(" ", "_").replace("-_", "_"))
            with open(path, "wb") as f:
                f.write(blob)
            hits += 1
            last_hit = last_hit or label
            first_hit = label
            print(f"  {label}  OK    {len(blob):>7,} bytes")
        else:
            misses += 1
            extra = f"  ({describe_body(blob)})" if blob else ""
            print(f"  {label}  --    {status or 'no response'}{extra}")
        time.sleep(delay)

    print(f"\n  {hits} found, {misses} missing")
    if hits:
        print(f"  range: {first_hit} to {last_hit}")
        print(f"  saved to {out_dir}")
        if hits >= 12:
            print("\n  12+ monthly points — clears MIN_HISTORY_MONTHS.")
            print("  This fund can be scored once the NAVs are extracted.")
        else:
            print(f"\n  Only {hits} points. Needs 12 to score; try --months higher,")
            print("  or the naming convention may change further back.")
    else:
        print("\n  Nothing found. The folder or prefix is wrong.")
        print("  Open the factsheet page in a browser, right-click a PDF link,")
        print("  copy the address, and read the exact folder and filename from it.")
    return 0 if hits else 1


def probe(folder: str, prefix: str, start: date, suffix: str,
          year_dir: bool = True) -> int:
    """Test three recent months before committing to a long crawl."""
    print(f"Probing: {ROOT}/{folder}/{prefix}<Month> <Year>{suffix}.pdf\n")
    warm_session()
    found = 0
    for i in (0, 1, 2):
        when = month_back(start, i)
        url, status, blob = fetch_month(folder, prefix, when, suffix, 0.4)
        ok = status == 200 and is_pdf(blob)
        found += ok
        print(f"  {MONTHS[when.month-1][:3]} {when.year}: {'HIT' if ok else 'miss'}  ({status})")
        if not ok and blob:
            print(f"    got {describe_body(blob)}")
        print(f"    {url}")
        time.sleep(1.5)

    if found:
        print(f"\n  {found}/3 — pattern confirmed, run without --probe")
        return 0
    print("\n  0/3 — the request is being refused or the path is wrong.")
    print("  If it says Cloudflare challenge, the site is blocking scripted")
    print("  access and the practical route is to download by hand, or to ask")
    print("  the provider directly for the series (ARCHITECTURE.md 17.6).")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default="",
                    help='fund subfolder; empty for the 2025 flat layout')
    ap.add_argument("--prefix", required=True, help='e.g. "PDIF Fact Sheet - "')
    ap.add_argument("--suffix", default="", help="anything after the year")
    ap.add_argument("--months", type=int, default=24)
    ap.add_argument("--out", default="data/factsheets")
    ap.add_argument("--start", default="", help="YYYY-MM, default last month")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    ap.add_argument("--probe", action="store_true", help="test 3 months only")
    ap.add_argument("--no-year-dir", action="store_true",
                    help="omit the /<YEAR>/ path segment")
    args = ap.parse_args()

    if args.start:
        y, m = args.start.split("-")
        start = date(int(y), int(m), 1)
    else:
        start = month_back(date.today(), 0)

    if args.probe:
        return probe(args.folder, args.prefix, start, args.suffix,
                     not args.no_year_dir)

    out = os.path.join(args.out, args.folder.replace(" ", "_"))
    print(f"Fetching {args.months} months back from "
          f"{MONTHS[start.month-1]} {start.year}\n")
    return run(args.folder, args.prefix, args.months, out, start,
               args.delay, args.suffix, not args.no_year_dir)


if __name__ == "__main__":
    sys.exit(main())

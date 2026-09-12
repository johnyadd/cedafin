"""
fetch_gse_archive.py — read the archive, do not guess the filename.

WHY THE EXISTING FETCHER MISSES
fetch_gse_reports.py builds a URL from the data month and assumes the report
is filed the following month. Both assumptions fail:

    .../2026/07/GSE-Equities-Market-Report-May-2026-compressed-1.pdf

The May report is filed under JULY — two months late, not one. And the name
ends "-compressed-1", where the -1 is WordPress's collision suffix, added
because a file of that name already existed when somebody re-uploaded it.

Nothing predicts a collision suffix. A guessing fetcher will miss that report
for ever, which is how May 2025, April 2026 and May 2026 came to be holes in a
series the brokers page computes across.

WHAT IS DIFFERENT ABOUT THE GSE
Bank of Ghana publishes the current APR notice and removes the last one — we
checked eight earlier months and found nothing. The Exchange is the opposite:
their Market Reports page carries year tabs back to 2017.

So GSE gaps are RECOVERABLE and BoG gaps are not. Two archives, two problems,
and worth keeping the distinction in mind before assuming a missing file is
gone.

WHAT THIS DOES
Reads the Market Reports page, takes every equities report link out of it,
works out which data month each covers from the filename rather than the
folder, and downloads anything not already held.

The year tabs are rendered by JavaScript, but the links are in the HTML behind
them — a tab panel is hidden, not absent. Fetching the page plainly is enough.

Usage:
    python fetch_gse_archive.py --dry-run
    python fetch_gse_archive.py
    python fetch_gse_archive.py --all      # back to 2017, not just the gaps
"""

from __future__ import annotations

import argparse
import html
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

PAGE = "https://gse.com.gh/market-reports/"
OUT_DIR = "data/gse"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 CedafinBot/0.3"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "identity",
}

# Equities reports only. The Exchange also publishes Debt (GFIM) and Market
# Summary reports; those are separate series and would need their own
# extraction, so taking them here would fill data/gse with files nothing reads.
LINK_RX = re.compile(
    r'href="(https://gse\.com\.gh/wp-content/uploads/[^"]*'
    r'Equities[^"]*\.pdf)"',
    re.I,
)

MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        start=1,
    )
}


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
    except Exception:  # noqa: BLE001
        return 0, b""


def data_month(url: str) -> str | None:
    """
    The month the report COVERS, from the filename.

    Never from the folder. The May 2026 report sits in /2026/07/ because that
    is when it was uploaded — reading the folder would file it as July and the
    error would be invisible afterwards.
    """
    name = url.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").lower()
    year = re.search(r"\b(20\d{2})\b", name)
    if not year:
        return None
    for m, num in MONTHS.items():
        if re.search(rf"\b{m}\b", name):
            return f"{year.group(1)}-{num:02d}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true", help="fetch everything, not just gaps")
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    print(f"  reading {PAGE}")
    st, body = fetch(PAGE)
    if st != 200 or not body:
        print(f"  page returned {st} — cannot continue")
        return 1

    page = body.decode("utf-8", errors="replace")
    links: dict[str, str] = {}
    unknown = 0
    for m in LINK_RX.finditer(page):
        url = html.unescape(m.group(1))
        month = data_month(url)
        if not month:
            unknown += 1
            continue
        # A month appearing twice means a re-upload. Keep the later URL, which
        # is the corrected file — that is what the -1 suffix means.
        links[month] = url

    if not links:
        print("  no equities report links found.")
        print()
        print("  The page structure may have changed. Open it in a browser")
        print("  before concluding the reports are gone — the Exchange keeps")
        print("  an archive back to 2017, unlike Bank of Ghana.")
        return 1

    print(f"  {len(links)} equities report(s) linked", end="")
    print(f", {unknown} whose month could not be read" if unknown else "")

    os.makedirs(args.out, exist_ok=True)
    held = {
        m.group(0)
        for f in os.listdir(args.out)
        if (m := re.search(r"\d{4}-\d{2}", f))
    }

    wanted = sorted(links)
    missing = [m for m in wanted if m not in held]

    print(f"  {len(held)} already held, {len(missing)} not")
    print()

    todo = wanted if args.all else missing
    if not todo:
        print("  Nothing to fetch. The series is complete for what the page offers.")
        return 0

    for month in todo:
        state = "held" if month in held else "NEW"
        print(f"    {month}  {state:<5} {links[month].rsplit('/', 1)[-1][:60]}")

    if args.dry_run:
        print()
        print("  Dry run — nothing downloaded.")
        return 0

    print()
    got = skipped = 0
    for month in todo:
        target = os.path.join(args.out, f"gse-{month}.pdf")
        if os.path.exists(target) and not args.all:
            skipped += 1
            continue
        time.sleep(args.delay)
        st2, blob = fetch(links[month])
        if st2 != 200 or not blob:
            print(f"    {month}: download failed ({st2})")
            continue
        with open(target, "wb") as fh:
            fh.write(blob)
        print(f"    {month}: saved {len(blob):,} bytes")
        got += 1

    print()
    print(f"  {got} new, {skipped} already held")
    if got:
        print()
        print("  Run extract_gse.py, then load_gse.py — and check_consistency.py")
        print("  after, since the broker series is computed from these.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

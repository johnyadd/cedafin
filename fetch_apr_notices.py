"""
fetch_apr_notices.py — read the page, do not guess the filename.

WHY THE EXISTING FETCHER FAILS
fetch_apr.py builds URLs from a pattern and tries three variants per month. It
finds May 2026 and misses April and March, and its own output says the honest
thing: guessing filenames has cost more rounds on this project than reading a
page ever has.

It cannot work because Bank of Ghana's naming is not systematic. May 2026 sits
at /wp-content/uploads/2026/07/MAY-APR-2026.pdf — published two months late,
filed in a folder named for the publication month rather than the data month,
and named MAY-APR rather than APR-May. No pattern derived from one month
predicts the next.

That is why the APR job was left out of the scheduled workflow. A fetcher that
guesses would fail silently most months and nobody would notice.

WHAT THIS DOES INSTEAD
Reads the Bank's own search results for APR notices, follows each notice, and
takes the PDF link out of the page body. Whatever they have published, it
finds — and when next month arrives under some new naming convention, this
keeps working.

WHAT IT CANNOT FIX
Bank of Ghana appears to keep only the current APR notice published. Eight
earlier months were checked and no notice exists for any of them. So this
fetches what is available now; it cannot recover a back series, because the
back series is not there to recover.

Which is the argument for scheduling it. Each month's report is up for a while
and then is not. Anything not collected while it is available is gone, and the
only archive is the one you keep.

Usage:
    python fetch_apr_notices.py --dry-run
    python fetch_apr_notices.py
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

SEARCH_URL = "https://www.bog.gov.gh/?s=APR"
OUT_DIR = "data/apr"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 CedafinBot/0.3"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "identity",
}

# A notice about the APR publication, not one of the many results the site
# returns for "APR" that are really about the month of April.
APR_NOTICE_RX = re.compile(
    r'href="(https://www\.bog\.gov\.gh/notice/[^"]*'
    r'(?:annual|annualiz|annualis)[a-z\-]*[^"]*percentage[^"]*)"',
    re.I,
)

PDF_RX = re.compile(r'href="(https://www\.bog\.gov\.gh/wp-content/[^"]+\.pdf)"', re.I)

MONTHS = {
    name.lower(): i
    for i, name in enumerate(
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


def fetch(url: str, timeout: int = 30) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return getattr(r, "status", 200), r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:  # noqa: BLE001
        return 0, b""


def data_month(text: str) -> str | None:
    """
    The month the data covers, from a notice URL or title.

    'as-at-may-2026' gives 2026-05. Returns None rather than guessing when the
    text names no month and year — a file saved under the wrong month is worse
    than one not saved at all, because the error is invisible afterwards.
    """
    t = text.lower().replace("-", " ").replace("_", " ")
    year = re.search(r"\b(20\d{2})\b", t)
    if not year:
        return None
    for name, num in MONTHS.items():
        if re.search(rf"\b{name}\b", t):
            return f"{year.group(1)}-{num:02d}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    print(f"  reading {SEARCH_URL}")
    st, body = fetch(SEARCH_URL)
    if st != 200 or not body:
        print(f"  search page returned {st} — cannot continue")
        return 1

    page = body.decode("utf-8", errors="replace")
    notices: list[str] = []
    for m in APR_NOTICE_RX.finditer(page):
        url = html.unescape(m.group(1))
        if url not in notices:
            notices.append(url)

    if not notices:
        print("  no APR notices linked from the search page.")
        print()
        print("  Either the Bank has changed how it publishes these, or the")
        print("  search markup has changed. Open the URL above in a browser")
        print("  before concluding the report is missing — this script exists")
        print("  precisely because assuming was what went wrong last time.")
        return 1

    print(f"  {len(notices)} APR notice(s) linked")
    print()

    os.makedirs(args.out, exist_ok=True)
    found: list[tuple[str, str, str]] = []

    for notice in notices:
        time.sleep(args.delay)
        st2, nbody = fetch(notice)
        if st2 != 200 or not nbody:
            print(f"    unreachable ({st2}): {notice}")
            continue

        npage = nbody.decode("utf-8", errors="replace")
        pdfs = [html.unescape(x) for x in PDF_RX.findall(npage)]
        if not pdfs:
            print(f"    no PDF linked from {notice}")
            continue

        # Month from the notice URL first: it names the DATA month, whereas the
        # PDF path names the publication month. MAY-APR-2026.pdf lives in a
        # folder called 2026/07.
        month = data_month(notice) or data_month(pdfs[0])
        if not month:
            print(f"    could not determine the data month: {notice}")
            continue

        found.append((month, pdfs[0], notice))

    if not found:
        print("  no PDFs found behind any notice.")
        return 1

    print(f"  {len(found)} report(s) located:")
    for month, pdf, _ in sorted(found):
        target = os.path.join(args.out, f"apr-{month}.pdf")
        state = "already held" if os.path.exists(target) else "NEW"
        print(f"    {month}   {state:<12} {pdf.rsplit('/', 1)[-1]}")

    if args.dry_run:
        print()
        print("  Dry run — nothing downloaded.")
        return 0

    print()
    downloaded = skipped = 0
    for month, pdf, _ in sorted(found):
        target = os.path.join(args.out, f"apr-{month}.pdf")
        if os.path.exists(target):
            skipped += 1
            continue
        time.sleep(args.delay)
        st3, blob = fetch(pdf)
        if st3 != 200 or not blob:
            print(f"    {month}: download failed ({st3})")
            continue
        with open(target, "wb") as fh:
            fh.write(blob)
        print(f"    {month}: saved {len(blob):,} bytes")
        downloaded += 1

    print()
    print(f"  {downloaded} new, {skipped} already held")
    if downloaded:
        print()
        print("  Run extract_apr.py, then load_lending_products.py.")
    else:
        print()
        print("  Nothing new — the expected result between releases, since the")
        print("  Bank keeps only the current notice published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

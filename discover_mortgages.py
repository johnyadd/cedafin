"""
discover_mortgages.py — what Ghanaian banks publish about home loans.

WHY THIS EXISTS
A strategy note quoted Republic Bank at 18% a year. Republic's own mortgage
calculator page says 27% up to ten years and 28% beyond it. The 18% came from
a third-party aggregator.

Three aggregator sites gave three different figures for the same banks —
Absa at 22%, Stanbic at 21-24%, Fidelity at 21-25%, GCB at 15.9% — none of
them sourced to the bank, none agreeing with the others.

So the same pattern as everywhere else on this site: providers publish little,
aggregators fill the gap, and the numbers do not reconcile. The only way to
know is to read what each bank says on its own pages.

WHY IT MATTERS MORE HERE THAN USUAL
Mortgage rates at 27% against prime rental yields of 8-11% mean a leveraged
property loses roughly three times its rental income in interest. If that is
right it is the most consequential single figure we could publish about
Ghanaian property — which is exactly why it cannot come from an aggregator.

WHAT IT DOES
Reads the pages each bank publishes about mortgages, and reports what it finds:
a rate, a term, a loan-to-value, a fee, or nothing. Reports the absence as
plainly as the presence, because the absence is the finding.

WHAT IT DOES NOT DO
Decide anything. It prints what it found and where, for a human to read and
verify before a figure goes anywhere near the database. Every earlier scan on
this project that tried to be clever about extraction produced numbers that
had to be corrected later.

Usage:
    python discover_mortgages.py
    python discover_mortgages.py --bank republic
"""

from __future__ import annotations

import argparse
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "identity",
}

# Bank, and the pages it publishes about home loans. Paths guessed from site
# structure get checked; a miss is recorded rather than retried differently,
# because guessing filenames has cost more rounds on this project than
# reading a page ever has.
BANKS: list[tuple[str, str, list[str]]] = [
    (
        "republic",
        "Republic Bank Ghana",
        [
            "https://republicghana.com/products/mortgage/mortgage-calculate/",
            "https://republicghana.com/products/mortgage/",
        ],
    ),
    (
        "stanbic",
        "Stanbic Bank Ghana",
        [
            "https://www.stanbicbank.com.gh/ghana/personal/products-and-services/borrow-for-your-needs/home-loans",
            "https://www.stanbicbank.com.gh/ghana/personal/borrow-for-your-needs",
        ],
    ),
    (
        "absa",
        "Absa Bank Ghana",
        [
            "https://www.absa.com.gh/personal/borrow/home-loans/",
            "https://www.absa.com.gh/personal/borrow/",
        ],
    ),
    (
        "fidelity",
        "Fidelity Bank Ghana",
        [
            "https://www.fidelitybank.com.gh/personal/loans/mortgage/",
            "https://www.fidelitybank.com.gh/personal/loans/",
        ],
    ),
    (
        "gcb",
        "GCB Bank",
        [
            "https://www.gcbbank.com.gh/personal-banking/loans/mortgage",
            "https://www.gcbbank.com.gh/personal-banking/loans",
        ],
    ),
    (
        "ecobank",
        "Ecobank Ghana",
        [
            "https://ecobank.com/gh/personal-banking/borrowing/home-loans",
            "https://ecobank.com/gh/personal-banking/borrowing",
        ],
    ),
    (
        "cal",
        "CalBank",
        [
            "https://www.calbank.net/personal/loans/mortgage",
            "https://www.calbank.net/personal/loans",
        ],
    ),
    (
        "firstatlantic",
        "First Atlantic Bank",
        ["https://firstatlanticbank.com.gh/personal/loans/"],
    ),
]

# What we are looking for on the page. A percentage near a mortgage word is a
# candidate, not an answer — a human reads the context before anything is
# recorded.
RATE = re.compile(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", re.I)
TERM = re.compile(r"(?:up to|maximum of|max(?:imum)?)\s*(\d{1,2})\s*years?", re.I)
LTV = re.compile(r"(?:up to\s*)?(\d{2,3})\s*%\s*(?:of the\s*)?(?:property|value|finance|LTV)", re.I)

CONTEXT = re.compile(
    r"(mortgage|home loan|house|property|LTV|loan[- ]to[- ]value|tenor|"
    r"interest rate|per annum|p\.a\.)",
    re.I,
)


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 30) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return getattr(r, "status", 200), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001
        return 0, ""


def strip(html: str) -> str:
    html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def snippets(text: str) -> list[str]:
    """Sentences containing both a percentage and a mortgage word."""
    out = []
    for part in re.split(r"(?<=[.!?])\s+|\s{2,}", text):
        if len(part) > 400:
            continue
        if RATE.search(part) and CONTEXT.search(part):
            out.append(part.strip())
    # Deduplicate while keeping order.
    seen = set()
    keep = []
    for s in out:
        k = s.lower()[:80]
        if k not in seen:
            seen.add(k)
            keep.append(s)
    return keep[:6]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    banks = [b for b in BANKS if not args.bank or b[0] == args.bank]

    found = silent = unreachable = 0

    for slug, name, urls in banks:
        print()
        print(f"  === {name} ===")
        got_any = False
        reached = False

        for url in urls:
            time.sleep(args.delay)
            status, html = fetch(url)
            if status != 200 or not html:
                print(f"    {status or 'no response'}  {url}")
                continue

            reached = True
            text = strip(html)
            hits = snippets(text)
            if not hits:
                print(f"    200 but nothing about rates  {url}")
                continue

            got_any = True
            print(f"    {url}")
            for h in hits:
                print(f"      {h[:200]}")

        if got_any:
            found += 1
        elif reached:
            silent += 1
            print("    -> site reachable, publishes no rate we could find")
        else:
            unreachable += 1
            print("    -> could not reach any mortgage page")

    print()
    print(f"  {found} publish something, {silent} silent, {unreachable} unreachable")
    print()
    print("  Nothing here goes into the database until a human has read the")
    print("  page and confirmed what the figure applies to. A percentage near")
    print("  the word mortgage is a candidate, not a rate — it might be an")
    print("  LTV, a fee, or last year's promotion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

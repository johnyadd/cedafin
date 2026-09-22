"""
check_page_claims.py — what the site SAYS, checked the way the data already is.

WHY THIS EXISTS
The data layer has rules and a daily check. The pages did not. Each worked out
its own counts and typed others in, so "37 verified funds", "106 funds",
"six of 50 fund managers" and "24 licensed stockbrokers" all went live while
the database underneath was right. Counts are now defined once, in
getSiteCounts (lib/data/funds.ts), and published at /api/counts. This check
keeps pages honest to it.

TWO CHECKS
1. Typed counts in the code. A number next to "funds", "banks", "brokers"
   and the like, in page text, fails — because it will go stale. Skipped:
   code comments, and DATED claims (a line naming a month and year, such as
   "May 2026", describes a moment and stays true). Anything else needs an
   entry in ALLOW below, with the reason written down.

2. Live pages against /api/counts. Pages that print counts are fetched from
   the site and their numbers compared with what the counts module says.
   /funds still does its own sums for its lists, so this is what catches it
   the day it drifts.

Run:  python check_page_claims.py            (both checks)
      python check_page_claims.py --code     (typed counts only, no network)
Exits non-zero on any failure, like check_consistency.py.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.request

SITE = "https://www.cedafin.com"
UA = "Mozilla/5.0 (compatible; CedafinCheck/1.0; +https://www.cedafin.com/methodology)"

NOUNS = (
    r"funds|banks|brokers|stockbrokers|companies|lenders|providers|"
    r"fund managers|firms|savings and loans"
)
TYPED = re.compile(rf"\b\d{{1,3}} (?:Ghanaian )?(?:{NOUNS})\b")
DATED = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December) 20\d\d"
)

# Permitted typed counts. Each needs a reason a reader of this file accepts.
# Match on (file ending, text on the line).
ALLOW: list[tuple[str, str, str]] = [
    (
        "app/api/card/[finding]/route.tsx",
        "of 22 banks",
        "A finding card about the May 2026 return; the image states the return.",
    ),
    (
        "app/page.tsx",
        '"22 banks"',
        "Homepage lending tabs — pending: each tab should count what it shows.",
    ),
    (
        "app/page.tsx",
        '"21 banks"',
        "Homepage lending tabs — pending: each tab should count what it shows.",
    ),
    (
        "app/is-it-licensed/page.tsx",
        "9 private funds",
        "From the SEC private funds register snapshot, which getSiteCounts does not yet read.",
    ),
]


def strip_comments(text: str) -> str:
    """Blank out /* ... */ blocks, keeping line numbers, and // comment lines."""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), text, flags=re.S)
    return "\n".join("" if l.lstrip().startswith("//") else l for l in text.split("\n"))


def check_code(root: str) -> list[str]:
    failures: list[str] = []
    for base in ("app", "components"):
        for dirpath, _, files in os.walk(os.path.join(root, base)):
            for fn in files:
                if not fn.endswith((".tsx", ".ts")):
                    continue
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, root).replace("\\", "/")
                with open(path, encoding="utf-8") as fh:
                    lines = strip_comments(fh.read()).split("\n")
                for i, line in enumerate(lines, 1):
                    if not TYPED.search(line) or DATED.search(line):
                        continue
                    if any(rel.endswith(f) and s in line for f, s, _ in ALLOW):
                        continue
                    failures.append(f"{rel}:{i}: {line.strip()[:110]}")
    return failures


def fetch(path: str) -> str:
    req = urllib.request.Request(SITE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def text_of(page: str) -> str:
    page = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


def check_live() -> list[str]:
    failures: list[str] = []
    counts = json.loads(fetch("/api/counts"))

    def expect(page: str, label: str, pattern: str, key: str) -> None:
        m = re.search(pattern, page)
        if not m:
            failures.append(f"{label}: could not find the figure (pattern {pattern!r}) — page changed?")
            return
        shown = int(m.group(1))
        if shown != counts[key]:
            failures.append(f"{label}: page shows {shown}, /api/counts {key} = {counts[key]}")

    funds = text_of(fetch("/funds"))
    expect(funds, "/funds tracked", r"(\d+) Ghanaian funds tracked", "fundsTracked")
    expect(funds, "/funds verified", r"tracked · (\d+) with verified", "fundsVerified")

    lic = text_of(fetch("/is-it-licensed"))
    expect(lic, "/is-it-licensed funds", r"(\d+) funds\b", "fundsTracked")
    expect(lic, "/is-it-licensed stockbrokers", r"(\d+) stockbrokers\b", "stockbrokersTrading")
    expect(lic, "/is-it-licensed banks", r"(\d+) banks\b", "banks")
    expect(lic, "/is-it-licensed savings and loans", r"(\d+) savings and loans companies", "savingsAndLoans")
    expect(lic, "/is-it-licensed listed", r"(\d+) listed companies", "listedCompanies")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", action="store_true", help="typed counts only, no network")
    args = ap.parse_args()
    root = os.path.dirname(os.path.abspath(__file__))

    print()
    print("  Page claims — what the site says, against what it knows")
    print()

    code = check_code(root)
    if code:
        print(f"  {len(code)} typed count(s) in page text:")
        for f in code:
            print(f"    {f}")
    else:
        print("  ok    no typed counts outside comments, dated claims and the allow list")

    live: list[str] = []
    if not args.code:
        try:
            live = check_live()
        except Exception as e:  # a site that cannot be read is a failure, not a pass
            live = [f"could not read the live site: {e}"]
        print()
        if live:
            print(f"  {len(live)} page(s) disagreeing with /api/counts:")
            for f in live:
                print(f"    {f}")
        else:
            print("  ok    /funds and /is-it-licensed agree with /api/counts")

    failed = bool(code or live)
    if failed:
        print()
        print("  A typed count goes stale; a page doing its own sums drifts. Fix the")
        print("  page to read getSiteCounts, date the claim, or add it to ALLOW with")
        print("  the reason written down.")
    print()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

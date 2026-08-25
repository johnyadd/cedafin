"""
discover_lender_terms.py — which banks actually publish their lending terms?

WHY THIS EXISTS
The lender page was about to tell 22 banks we hold none of their product
details. True — but a bank whose SME loan page lists facility name, eligibility
and minimum would reasonably reply "it is on our website", and the ask would
look like we had not looked. Asking someone for what they already publish is
the fastest way to be ignored.

So: check first. This visits each bank's site, finds pages that look like
business lending, and records which product fields appear on them.

WHAT IT DOES NOT DO
It does not extract the terms. Finding that a page mentions a minimum is a
different job from reading it correctly, and every extraction on this project
has needed the dump-then-write loop against real markup. This answers one
question — WHERE is there something to read — and leaves reading it to a
per-bank pass afterwards.

It also does not judge. A bank with no lending page may sell entirely through
relationship managers, which is normal in Ghana and not a failing. The output
is a map of where to look, not a scorecard.

MANNERS
Two requests a second at most, a truthful user agent, and each site is visited
a handful of times, not crawled. robots.txt is checked and honoured — several
of these are large institutions and a comparison site has no business ignoring
a stated crawl preference. Where robots.txt disallows, the bank is recorded as
"ask directly" rather than skipped silently.

Usage:
    python discover_lender_terms.py --limit 3     # try a few first
    python discover_lender_terms.py
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (compatible; CediWiseBot/0.1; "
                   "comparison site data check)"),
    "Accept": "text/html,application/xhtml+xml,*/*",
}

# Paths a business-lending page tends to live at. Tried in order; the first
# few that return HTML are scanned.
CANDIDATE_PATHS = [
    "", "/business", "/business-banking", "/sme", "/sme-banking",
    "/business/loans", "/business-loans", "/loans", "/products/loans",
    "/corporate", "/business/sme", "/personal/loans",
]

# A link whose text or href suggests business lending.
LENDING_LINK = re.compile(
    r"\b(sme|business\s*loan|business\s*bank|working\s*capital|overdraft|"
    r"term\s*loan|asset\s*financ|invoice|trade\s*financ|credit\s*facilit|"
    r"lending|borrow)\b",
    re.I,
)

# Signals that a page carries actual TERMS rather than marketing.
FIELD_SIGNALS = {
    "facility_name": re.compile(
        r"\b(working capital|overdraft|term loan|asset financ\w*|invoice "
        r"discount\w*|trade financ\w*|revolving|bridge financ\w*)\b", re.I),
    "minimum": re.compile(
        r"\bminimum\b[^.]{0,60}(GH[¢C₵]|GHS|cedi)|\b(GH[¢C₵]|GHS)\s?[\d,]{3,}",
        re.I),
    "security": re.compile(
        r"\b(collateral|security|guarantee|lien|charge over|pledge)\b", re.I),
    "eligibility": re.compile(
        r"\b(eligib\w+|qualify|requirements?|who can apply|criteria)\b", re.I),
    "turnaround": re.compile(
        r"\b(\d+\s*(working\s*)?(hours?|days?)|same[- ]day|turnaround|"
        r"within\s*\d+)\b", re.I),
    "rate": re.compile(
        r"\b(interest rate|APR|from\s*\d{1,2}(\.\d+)?\s*%|\d{1,2}(\.\d+)?\s*%\s*"
        r"(p\.?a\.?|per annum))\b", re.I),
    "tenor": re.compile(
        r"\b(up to\s*\d+\s*(months?|years?)|tenor|repayment period|"
        r"\d+\s*[- ]?\s*(month|year)\s*(term|tenor))\b", re.I),
}


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            ctype = r.headers.get("Content-Type", "")
            if "html" not in ctype.lower():
                return 0, ""
            return getattr(r, "status", 200), r.read(600_000).decode(
                "utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:                                        # noqa: BLE001
        return 0, ""


def robots_allows(base: str) -> bool | None:
    """
    None means no robots.txt — no preference expressed, proceed politely.
    False means a blanket disallow for everyone.
    """
    status, txt = fetch(urllib.parse.urljoin(base, "/robots.txt"))
    if status != 200 or not txt:
        return None
    blocked = False
    applies = False
    for line in txt.splitlines():
        line = line.strip()
        if re.match(r"(?i)^user-agent:\s*\*", line):
            applies = True
            continue
        if re.match(r"(?i)^user-agent:", line):
            applies = False
            continue
        if applies and re.match(r"(?i)^disallow:\s*/\s*$", line):
            blocked = True
    return not blocked


def strip_tags(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def lending_links(html: str, base: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r'href=["\']([^"\']+)["\'][^>]*>(.{0,120}?)</a>',
                         html, re.I | re.S):
        href, label = m.group(1), strip_tags(m.group(2))
        if not LENDING_LINK.search(f"{href} {label}"):
            continue
        full = urllib.parse.urljoin(base, href)
        if urllib.parse.urlparse(full).netloc != urllib.parse.urlparse(base).netloc:
            continue
        if full.rstrip("/") == base.rstrip("/") or full in out:
            continue
        out.append(full)
        if len(out) >= 6:
            break
    return out


def scan(text: str) -> dict[str, bool]:
    return {k: bool(rx.search(text)) for k, rx in FIELD_SIGNALS.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--register", default="bog_lenders.csv")
    ap.add_argument("--out", default="lender_terms_discovery.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.6)
    args = ap.parse_args()

    if not os.path.exists(args.register):
        print(f"{args.register} not found — run fetch_bog_registers.py first.")
        return 1

    banks = [
        r for r in csv.DictReader(open(args.register, encoding="utf-8"))
        if "bank" in (r.get("category") or "").lower()
        and "community" not in (r.get("category") or "").lower()
        and (r.get("website") or "").startswith("http")
    ]
    if args.limit:
        banks = banks[: args.limit]
    print(f"Checking {len(banks)} bank website(s)\n")

    rows = []
    for b in banks:
        name = b["name"]
        base = b["website"].rstrip("/")
        allowed = robots_allows(base)
        if allowed is False:
            print(f"  {name[:34]:<36} robots.txt disallows — ask directly")
            rows.append({
                "bank": name, "website": base, "status": "robots_disallow",
                "pages_found": 0, "best_page": "",
                **{k: "" for k in FIELD_SIGNALS},
            })
            time.sleep(args.delay)
            continue

        # Home page first, then whatever it links to that looks like lending.
        status, home = fetch(base)
        if status != 200 or not home:
            print(f"  {name[:34]:<36} site unreachable")
            rows.append({
                "bank": name, "website": base, "status": "unreachable",
                "pages_found": 0, "best_page": "",
                **{k: "" for k in FIELD_SIGNALS},
            })
            time.sleep(args.delay)
            continue

        pages = lending_links(home, base)
        if not pages:
            for p in CANDIDATE_PATHS[1:6]:
                pages.append(base + p)

        best: tuple[int, str, dict] | None = None
        checked = 0
        for url in pages[:6]:
            st, html = fetch(url)
            time.sleep(args.delay)
            if st != 200 or not html:
                continue
            checked += 1
            found = scan(strip_tags(html))
            score = sum(found.values())
            if best is None or score > best[0]:
                best = (score, url, found)

        if best is None:
            print(f"  {name[:34]:<36} no lending page found")
            rows.append({
                "bank": name, "website": base, "status": "no_page_found",
                "pages_found": checked, "best_page": "",
                **{k: "" for k in FIELD_SIGNALS},
            })
            continue

        score, url, found = best
        have = [k for k, v in found.items() if v]
        print(f"  {name[:34]:<36} {score}/7  {', '.join(have) or 'nothing'}")
        rows.append({
            "bank": name, "website": base, "status": "checked",
            "pages_found": checked, "best_page": url,
            **{k: ("yes" if v else "no") for k, v in found.items()},
        })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    checked = [r for r in rows if r["status"] == "checked"]
    withrate = [r for r in checked if r.get("rate") == "yes"]
    withmin = [r for r in checked if r.get("minimum") == "yes"]
    print(f"\n  {len(rows)} bank(s) -> {args.out}")
    print(f"    {len(checked)} with a readable lending page")
    print(f"    {len(withrate)} mention a rate")
    print(f"    {len(withmin)} mention a minimum")
    print("\n  A SIGNAL IS NOT A TERM. This says a page mentions something")
    print("  rate-shaped or minimum-shaped, not that the figure is correct or")
    print("  current. Read the page before publishing anything from it — and")
    print("  before telling a bank we hold nothing, check this file first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
discover_lending_criteria.py — what a bank asks for, take two.

WHY THIS IS A REWRITE
The first version reported Fidelity Bank as having no reachable website.
Fidelity publishes the most detailed SME lending criteria of any bank in
Ghana — turnover thresholds, minimum months of relationship, dud-cheque
limits, facility caps by customer tenure. The scan missed all of it.

Three other banks came back dead the same way, and Standard Chartered returned
two pages when its business section runs to dozens. So the first version's
finding — that banks do not publish eligibility — was a fact about the scanner.

TWO CHANGES, AND THE SECOND MATTERS MORE

  A browser-shaped request. Large Ghanaian banks sit behind bot protection
  that returns 403 or a challenge to a bare urllib call. A full header set,
  redirect following and one retry gets past most of it.

  Paths read rather than guessed. The first version tried a fixed list of
  fifteen URLs per bank. This reads the home page, extracts every internal
  link, and follows the ones whose text or href suggests business lending.

  That second change is the lesson of this whole project. Guessing filenames
  and paths has cost more rounds than anything else — the Bank of Ghana APR
  fetcher, the SEC REIT register, the broker fee pages. Reading a page's own
  navigation has worked every time.

WHAT IT LOOKS FOR
Six things, and they are deliberately narrow. A bank site is mostly marketing,
and a loose pattern returns menu items — the first version matched "Security
Centre" and "Security Tips" seventeen times and found one real requirement.

  turnover     — a credit turnover or revenue threshold
  trading      — minimum time in business
  relationship — minimum months banking with them
  documents    — what must be produced
  security     — collateral, guarantee, cash cover
  facility     — minimum or maximum amount

WHAT IT STILL CANNOT SHOW
Whether meeting the criteria gets you the loan, or the rate. A bank may
publish modest requirements and decline most applicants. Requirements are not
a risk model.

Usage:
    python discover_lending_criteria.py --limit 3
    python discover_lending_criteria.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# A bare urllib request gets 403 from most bank sites. This is what a browser
# sends, minus the things that would be dishonest to claim.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 CedafinBot/0.3"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "close",
    "Upgrade-Insecure-Requests": "1",
}

# Link text or href fragments that suggest business lending. Used to decide
# which of a home page's links to follow.
FOLLOW_RX = re.compile(
    r"business|sme|corporate|loan|lend|borrow|credit|overdraft|finance|"
    r"working.capital|trade|asset|product",
    re.I,
)

# Pages not worth fetching even if they match above.
SKIP_RX = re.compile(
    r"\.(pdf|jpg|jpeg|png|gif|zip|docx?|xlsx?)$|"
    r"login|signin|register|careers|news|media|press|blog|privacy|cookie|"
    r"terms|sitemap|contact|branch|atm|swift|tender|vacanc",
    re.I,
)

TURNOVER_RX = re.compile(
    r"\b(credit\s+turnover|annual\s+turnover|monthly\s+turnover|turnover|"
    r"revenue|sales)\b[^.]{0,70}(GH[¢C₵]|GHS)\s?[\d,]{3,}"
    r"|(GH[¢C₵]|GHS)\s?[\d,]{3,}[^.]{0,50}\b(turnover|revenue|credit\s+turnover)\b",
    re.I,
)

TRADING_RX = re.compile(
    r"\b(minimum\s+of\s+)?(\d+|one|two|three|four|five|six)\s*"
    r"(year|month)s?\b[^.]{0,60}"
    r"\b(in\s+business|of\s+operation|active\s+operation|experience\s+in|"
    r"in\s+the\s+line\s+of\s+business|trading|operational)\b",
    re.I,
)

RELATIONSHIP_RX = re.compile(
    r"\b(\d+|one|two|three|six|twelve)\s*(month|year)s?\b[^.]{0,60}"
    r"\b(relationship|banking\s+with|account\s+with|maintained?\s+an?\s+account)\b"
    r"|\b(minimum\s+of\s+)?(\d+|six|twelve)\s*months?\b[^.]{0,40}"
    r"\b(relationship|with\s+the\s+bank)\b",
    re.I,
)

DOCS_RX = re.compile(
    r"\b(audited\s+(financial\s+)?(accounts|statements)|management\s+accounts|"
    r"tax\s+clearance|business\s+registration|certificate\s+of\s+incorporation|"
    r"bank\s+statements?|cash\s?flow\s+projection|business\s+plan)\b"
    r"[^.]{0,80}",
    re.I,
)

SECURITY_RX = re.compile(
    r"\b(collateral|cash\s+cover|cash\s+collateral|personal\s+guarantee|"
    r"corporate\s+guarantee|guarantor|landed\s+propert|title\s+deed|"
    r"lien\s+over|charge\s+over|unsecured|semi.?secured)\b[^.]{0,90}",
    re.I,
)

FACILITY_RX = re.compile(
    r"\b(maximum|up\s+to|capped\s+at|minimum|facility\s+(amount|size))\b"
    r"[^.]{0,50}(GH[¢C₵]|GHS)\s?[\d,]{3,}",
    re.I,
)

PATTERNS = [
    ("turnover", TURNOVER_RX),
    ("trading", TRADING_RX),
    ("relationship", RELATIONSHIP_RX),
    ("documents", DOCS_RX),
    ("security", SECURITY_RX),
    ("facility", FACILITY_RX),
]


def env() -> dict:
    if not os.path.exists(".env.local"):
        print("No .env.local — run from the project root.")
        sys.exit(1)
    out = {}
    for line in open(".env.local", encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


E = env()
BASE = E["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = E["SUPABASE_SERVICE_ROLE_KEY"]


def banks() -> list[dict]:
    q = (
        "/products?market_side=eq.borrow&asset_class=eq.sme_credit"
        "&lock_in_days=eq.365&select=rate_max,providers(slug,trading_name,website)"
        "&order=rate_max.asc"
    )
    req = urllib.request.Request(
        BASE + q, headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.loads(r.read())
    out, seen = [], set()
    for row in rows:
        p = row.get("providers") or {}
        slug = p.get("slug")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(
            {
                "slug": slug,
                "name": p.get("trading_name") or slug,
                "website": p.get("website") or "",
                "apr": row.get("rate_max"),
            }
        )
    return out


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 20, retry: bool = True) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            ctype = r.headers.get("Content-Type", "").lower()
            if "html" not in ctype:
                return 0, ""
            return getattr(r, "status", 200), r.read(800_000).decode(
                "utf-8", errors="replace"
            )
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001
        # One retry with a longer timeout. Several Ghanaian bank sites are slow
        # on a first hit and fine on a second.
        if retry:
            time.sleep(1.5)
            return fetch(url, timeout=timeout + 15, retry=False)
        return 0, ""


def strip_tags(h: str) -> str:
    h = re.sub(r"<(script|style|nav|footer)\b.*?</\1>", " ", h, flags=re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))


def internal_links(html: str, host: str) -> list[str]:
    """
    Every internal link whose href or anchor text suggests business lending.

    Reading the site's own navigation rather than guessing paths. Guessing has
    failed repeatedly on this project; reading has not.
    """
    out: list[str] = []
    for m in re.finditer(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S
    ):
        href, text = m.group(1), strip_tags(m.group(2))[:80]
        if SKIP_RX.search(href):
            continue
        if not (FOLLOW_RX.search(href) or FOLLOW_RX.search(text)):
            continue
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = f"https://{host}{href}"
        elif not href.startswith("http"):
            continue
        if host not in urllib.parse.urlparse(href).netloc:
            continue
        if href not in out:
            out.append(href)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="lending_criteria.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--max-pages", type=int, default=25)
    args = ap.parse_args()

    lenders = [b for b in banks() if b["website"]]
    if args.limit:
        lenders = lenders[: args.limit]

    print(f"Checking {len(lenders)} bank(s), cheapest APR first")
    print("Following each site's own links rather than guessing paths\n")
    rows = []

    for b in lenders:
        apr = f"{float(b['apr']) * 100:.2f}%" if b["apr"] is not None else "—"
        try:
            host = urllib.parse.urlparse(b["website"]).netloc.lower()
        except ValueError:
            host = ""
        if not host:
            print(f"  {b['name'][:28]:<30} {apr:>7}  no usable domain")
            continue

        st, home = fetch(f"https://{host}/")
        time.sleep(args.delay)
        if st != 200 or not home:
            # Try without www, or with it, before giving up.
            alt = host[4:] if host.startswith("www.") else f"www.{host}"
            st, home = fetch(f"https://{alt}/")
            time.sleep(args.delay)
            if st == 200 and home:
                host = alt

        if st != 200 or not home:
            print(f"  {b['name'][:28]:<30} {apr:>7}  UNREACHABLE ({st})")
            rows.append(
                {"bank": b["name"], "apr": apr, "domain": host, "pages": 0}
            )
            continue

        found = {k: "" for k, _ in PATTERNS}
        seen = {f"https://{host}/"}
        queue = internal_links(home, host)[: args.max_pages]
        docs = [home]

        for url in queue:
            if url in seen:
                continue
            seen.add(url)
            st2, page = fetch(url)
            time.sleep(args.delay)
            if st2 == 200 and page:
                docs.append(page)

        for page in docs:
            text = strip_tags(page)
            for key, rx in PATTERNS:
                if not found[key]:
                    m = rx.search(text)
                    if m:
                        found[key] = re.sub(r"\s+", " ", m.group(0))[:150].strip()

        hits = [k for k, v in found.items() if v]
        strong = len(hits) >= 3
        print(
            f"  {b['name'][:28]:<30} {apr:>7}  {len(docs):>2}p  "
            f"{', '.join(hits) or 'nothing'}{'  <- DETAILED' if strong else ''}"
        )

        rows.append(
            {"bank": b["name"], "apr": apr, "domain": host, "pages": len(docs), **found}
        )

    if rows:
        keys = sorted({k for r in rows for k in r})
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)

    print(f"\n  {len(rows)} bank(s) -> {args.out}")
    for key, _ in PATTERNS:
        n = sum(1 for r in rows if r.get(key))
        print(f"    {n:>2} publish something on {key}")
    unreachable = [r for r in rows if r.get("pages", 0) == 0]
    if unreachable:
        print(f"\n  {len(unreachable)} still unreachable:")
        for r in unreachable:
            print(f"    {r['bank']}")
        print("  Open one in a browser before concluding anything about them.")
    print()
    print("  Read every match. A pattern hit means the words appeared near a")
    print("  figure — the first version of this scan matched 'Security Centre'")
    print("  seventeen times and found one real requirement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

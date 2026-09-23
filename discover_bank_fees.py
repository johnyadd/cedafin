"""
discover_bank_fees.py — what a Ghanaian bank charges you to hold an account.

WHY THIS EXISTS
Every bank publishes a tariff guide, because Bank of Ghana requires it. Almost
nobody compares them. A business choosing a bank can find the loan rate — the
APR return makes that public — and cannot find what the account itself costs:
the monthly fee, the transfer charge, what a cash deposit costs, whether a
cheque book is free.

Those charges are small individually and large together. A business paying
GH¢25 a month, GH¢5 a transfer and 0.5% on cash deposits is paying more for
its banking than many pay in loan interest.

WHAT IT LOOKS FOR
Six patterns, each pairing a subject with a figure, because a bare keyword
matches menus. The lending scanner's first version matched "Security Centre"
seventeen times.

  monthly   — a monthly maintenance or service fee, with an amount
  transfer  — GHIPSS, RTGS, ACH or mobile money transfer charges
  cash      — cash deposit or withdrawal charges, flat or a percentage
  cheque    — cheque book issue or clearing fees
  card      — card issuance, annual card fees, SMS alert charges
  tariff    — a tariff guide or schedule of charges existing at all

WHAT IT CANNOT DO, AND WHY THAT IS STILL USEFUL
Most Ghanaian tariff guides are PDFs. This reads pages, not PDFs, so where a
bank publishes its charges in a document the scanner will usually find only
the link or the words around it — the "tariff" pattern. That is worth having:
whether a bank publishes a tariff guide at all is itself the first finding,
and the PDFs it names can then be fetched and read by hand, the way the
mortgage and savings pages were built.

A bank with no tariff hit is not proven to publish nothing. It means this scan
did not find it, on the date recorded — which is what the record says.

Usage:
    python discover_bank_fees.py --limit 3
    python discover_bank_fees.py
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
# What a diaspora account is called varies: Non-Resident Ghanaian Account,
# Diaspora Account, Foreign Currency Account, FCA, FEA, International Banking.
# "account" is loose enough to pull in dozens of ordinary pages, and it is
# kept anyway — the content patterns below do the filtering, and without it we
# would miss "Foreign Currency Account" entirely.
FOLLOW_RX = re.compile(
    r"tariff|fees|charges|pricing|service\s*guide|rates\s*and\s*charges|"
    r"account|current|business\s*bank|sme|personal\s*bank|schedule",
    re.I,
)

SKIP_RX = re.compile(
    r"login|signin|register|careers|news|media|press|blog|privacy|cookie|"
    r"terms|sitemap|contact|branch|atm-locator|swift|tender|vacanc",
    re.I,
)

# Pages not worth fetching even if they match above.
SKIP_RX = re.compile(
    r"\.(pdf|jpg|jpeg|png|gif|zip|docx?|xlsx?)$|"
    r"login|signin|register|careers|news|media|press|blog|privacy|cookie|"
    r"terms|sitemap|contact|branch|atm|swift|tender|vacanc",
    re.I,
)

# Each pattern pairs its subject with a figure. A bare keyword matches menus:
# the lending scanner's first version matched "Security Centre" seventeen
# times and found one real requirement.

AMOUNT = r"(?:GH[\u00a2C\u20b5]|GHS)\s?[\d,]+(?:\.\d{1,2})?|\d{1,2}(?:\.\d{1,2})?\s*%"

MONTHLY_RX = re.compile(
    r"\b(monthly\s+(account\s+)?(maintenance|service|fee)|account\s+maintenance|"
    r"ledger\s+fee|commission\s+on\s+turnover|\bCOT\b)\b[^.]{0,70}(" + AMOUNT + r")",
    re.I,
)

TRANSFER_RX = re.compile(
    r"\b(GHIPSS|RTGS|ACH|instant\s+pay|interbank\s+transfer|funds?\s+transfer|"
    r"mobile\s+money\s+transfer|wallet\s+transfer)\b[^.]{0,70}(" + AMOUNT + r")",
    re.I,
)

CASH_RX = re.compile(
    r"\b(cash\s+(deposit|withdrawal|handling)|over[- ]the[- ]counter|teller)\b"
    r"[^.]{0,70}(" + AMOUNT + r")",
    re.I,
)

CHEQUE_RX = re.compile(
    r"\b(cheque\s*(book|leaf|clearing|return)|chequebook)\b[^.]{0,70}(" + AMOUNT + r")",
    re.I,
)

CARD_RX = re.compile(
    r"\b(card\s+(issuance|replacement|annual|maintenance)|debit\s+card|"
    r"SMS\s+alert|e[- ]?statement|internet\s+banking\s+fee)\b[^.]{0,70}(" + AMOUNT + r")",
    re.I,
)

# Whether a tariff guide exists at all — the first finding, and the route to
# the PDFs a person then reads.
TARIFF_RX = re.compile(
    r"\b(tariff\s*(guide|sheet|schedule)?|schedule\s+of\s+(fees|charges)|"
    r"service\s+charges?\s+guide|rates\s+and\s+charges)\b[^.]{0,80}",
    re.I,
)

PATTERNS = [
    ("monthly", MONTHLY_RX),
    ("transfer", TRANSFER_RX),
    ("cash", CASH_RX),
    ("cheque", CHEQUE_RX),
    ("card", CARD_RX),
    ("tariff", TARIFF_RX),
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
    ap.add_argument("--out", default="bank_fees.csv")
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

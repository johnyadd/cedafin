"""
discover_broker_services.py — what each broker actually deals in.

THE QUESTION, AND WHY IT IS NARROWER THAN IT SOUNDS
Our brokers page says every licensed dealing member can trade every listed
share and the NewGold ETF — Ghanaian brokers do not specialise by company or
sector, and the exchange names no market makers. So "what shares do they
trade" has the same answer twenty-four times and is not worth asking.

What differs is everything else. Some deal in Treasury bills and bonds, some
run discretionary portfolios, some do corporate finance and nothing retail. A
saver who wants T-bills through a broker needs one that offers them, and there
is no list.

WHAT IT LOOKS FOR
Six service lines, each a real decision point for somebody choosing a firm:

  equities        — listed shares, the baseline every member can do
  fixed_income    — Treasury bills, notes, bonds, the GFIM market
  collective      — mutual funds or unit trusts they manage or distribute
  discretionary   — portfolio or wealth management, somebody else deciding
  advisory        — corporate finance, IPOs, capital raising, valuations
  custody         — nominee or custodial services, relevant to a non-resident

WHAT IT WILL NOT ESTABLISH
Whether they will take a retail client. A firm listing "wealth management"
may have a minimum of half a million cedis and no interest in a saver with
five thousand. Services offered is not services accessible, and the page will
have to say so.

BUILT ON WHAT THE EARLIER SCANS LEARNED
Reads each site's own navigation rather than guessing paths, uses a
browser-shaped request to get past bot protection, and prints every match for
reading rather than counting hits and trusting them.

Usage:
    python discover_broker_services.py --limit 3
    python discover_broker_services.py
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 CedafinBot/0.3"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "identity",
}

FOLLOW_RX = re.compile(
    r"service|product|solution|offer|invest|trade|trading|wealth|advisory|"
    r"corporate|about|what.we.do|brokerage|securities",
    re.I,
)

SKIP_RX = re.compile(
    r"\.(pdf|jpe?g|png|gif|zip|docx?|xlsx?)$|"
    r"login|signin|register|career|vacanc|privacy|cookie|terms|sitemap",
    re.I,
)

# Deliberately narrow. The first broker scan matched "Security Centre"
# seventeen times looking for collateral, which taught the lesson that a loose
# pattern finds navigation rather than substance.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "equities",
        re.compile(
            r"\b(equit(y|ies)\s+(trading|dealing|broking)|share\s+(dealing|"
            r"trading)|stock\s?broking|buy(ing)?\s+and\s+sell(ing)?\s+shares|"
            r"listed\s+(shares|equities))\b[^.]{0,80}",
            re.I,
        ),
    ),
    (
        "fixed_income",
        re.compile(
            r"\b(fixed[\s-]income|treasury\s+bills?|government\s+(bonds?|"
            r"securities)|corporate\s+bonds?|money\s+market\s+(instruments?|"
            r"securities)|GFIM)\b[^.]{0,80}",
            re.I,
        ),
    ),
    (
        "collective",
        re.compile(
            r"\b(mutual\s+funds?|unit\s+trusts?|collective\s+investment)\b"
            r"[^.]{0,80}",
            re.I,
        ),
    ),
    (
        "discretionary",
        re.compile(
            r"\b(discretionary|portfolio\s+management|wealth\s+management|"
            r"asset\s+management|managed\s+portfolio|investment\s+management)\b"
            r"[^.]{0,80}",
            re.I,
        ),
    ),
    (
        "advisory",
        re.compile(
            r"\b(corporate\s+finance|capital\s+rais|advisory\s+services|"
            r"initial\s+public\s+offer|IPO\s+|mergers?\s+and\s+acquisitions|"
            r"valuation\s+services|underwriting)\b[^.]{0,80}",
            re.I,
        ),
    ),
    (
        "custody",
        re.compile(
            r"\b(custod(y|ial|ian)|nominee\s+(services?|account)|"
            r"safekeeping)\b[^.]{0,80}",
            re.I,
        ),
    ),
]


def env() -> dict:
    out = {}
    if os.path.exists(".env.local"):
        for line in open(".env.local", encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    for k in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    if not out.get("NEXT_PUBLIC_SUPABASE_URL"):
        print("Missing Supabase credentials — run from the project root.")
        sys.exit(1)
    return out


E = env()
BASE = E["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = E["SUPABASE_SERVICE_ROLE_KEY"]


def brokers() -> list[dict]:
    req = urllib.request.Request(
        BASE + "/providers?slug=like.broker-*&select=slug,trading_name,website"
        "&order=trading_name.asc",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 20, retry: bool = True) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            if "html" not in r.headers.get("Content-Type", "").lower():
                return 0, ""
            return getattr(r, "status", 200), r.read(600_000).decode(
                "utf-8", errors="replace"
            )
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001
        if retry:
            time.sleep(1.5)
            return fetch(url, timeout=timeout + 12, retry=False)
        return 0, ""


def strip_tags(h: str) -> str:
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))


def internal_links(html: str, host: str) -> list[str]:
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
    ap.add_argument("--out", default="broker_services.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--max-pages", type=int, default=20)
    args = ap.parse_args()

    firms = [b for b in brokers() if (b.get("website") or "").strip()]
    if args.limit:
        firms = firms[: args.limit]

    print(f"Checking {len(firms)} broker website(s) for service lines\n")
    rows = []

    for b in firms:
        name = b["trading_name"] or b["slug"]
        try:
            host = urllib.parse.urlparse(
                b["website"] if "://" in b["website"] else f"https://{b['website']}"
            ).netloc.lower()
        except ValueError:
            host = ""
        if not host:
            print(f"  {name[:30]:<32} no usable domain")
            continue

        st, home = fetch(f"https://{host}/")
        time.sleep(args.delay)
        if st != 200 or not home:
            alt = host[4:] if host.startswith("www.") else f"www.{host}"
            st, home = fetch(f"https://{alt}/")
            time.sleep(args.delay)
            if st == 200 and home:
                host = alt

        if st != 200 or not home:
            print(f"  {name[:30]:<32} UNREACHABLE ({st})")
            rows.append({"broker": name, "domain": host, "pages": 0})
            continue

        found = {k: "" for k, _ in PATTERNS}
        docs = [home]
        for url in internal_links(home, host)[: args.max_pages]:
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
                        found[key] = re.sub(r"\s+", " ", m.group(0))[:120].strip()

        hits = [k for k, v in found.items() if v]
        print(
            f"  {name[:30]:<32} {len(docs):>2}p  {', '.join(hits) or 'nothing'}"
        )
        rows.append(
            {"broker": name, "domain": host, "pages": len(docs), **found}
        )

    if rows:
        keys = sorted({k for r in rows for k in r})
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)

    print(f"\n  {len(rows)} broker(s) -> {args.out}")
    for key, _ in PATTERNS:
        n = sum(1 for r in rows if r.get(key))
        print(f"    {n:>2} mention {key}")
    print()
    print("  Read the matches before publishing any of them. And remember what")
    print("  this cannot show: a firm listing wealth management may have a")
    print("  minimum of half a million cedis and no interest in a saver with")
    print("  five thousand. Services offered is not services accessible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

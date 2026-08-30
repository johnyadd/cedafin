"""
discover_broker_terms.py — do any Ghanaian brokers publish what they charge?

WHY THIS EXISTS
The broker page currently states that none of the twenty-four licensed dealing
members publishes a commission rate. That claim rests on the GSE reports and
the SEC register — neither of which would carry a rate even if the broker
published one on its own site. Nobody has looked at the sites.

The same pass over the twenty-four bank websites found real variation:
OmniBSIC and Standard Chartered publishing terms while most published nothing,
which turned one generic ask into four specific ones. There is no reason to
assume brokers are uniform either, and asserting it without checking is exactly
the sort of unverified claim this site refuses everywhere else.

WHAT IT LOOKS FOR, IN PRIORITY ORDER
    commission    the rate charged per trade — the missing number
    minimum       what it takes to open an account, which for a Ghanaian
                  saver is the more immediate barrier than the rate
    account_open  documents and process, since a Ghana Card requirement or a
                  branch visit is itself a gate
    online        whether trading can be done without visiting an office
    products      shares, bonds, bills, ETFs — what they say they deal in

Minimum matters more than commission for most people. Someone with GH¢1,000
who cannot open an account never reaches the question of what a trade costs.

WHAT IT DOES NOT DO
Extract the figures. Finding that a page mentions a commission rate is a
different job from reading it correctly, and every extraction on this project
has needed the dump-then-write loop against real markup. This answers where
there is something to read.

MANNERS
robots.txt is checked and honoured. Two requests a second at most, a handful of
pages per site, truthful user agent. Where a site disallows, the broker is
recorded as "ask directly" rather than skipped silently.

Usage:
    python discover_broker_terms.py --limit 3
    python discover_broker_terms.py
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
    "User-Agent": ("Mozilla/5.0 (compatible; CedafinBot/0.1; "
                   "comparison site data check)"),
    "Accept": "text/html,application/xhtml+xml,*/*",
}

CANDIDATE_PATHS = [
    "", "/services", "/brokerage", "/stockbroking", "/trading", "/invest",
    "/products", "/our-services", "/equities", "/how-to-invest",
    "/open-account", "/faq", "/fees", "/pricing",
]

LINK_HINT = re.compile(
    r"\b(brokerage|stockbrok|trading|equit|securit|invest|open[\s-]*account|"
    r"fees|pricing|charges|tariff|服务|service)\b", re.I)

SKIP = re.compile(r"\.(pdf|jpg|png|zip)$|mailto:|tel:|javascript:", re.I)

FIELD_SIGNALS = {
    # The number nobody is thought to publish. Deliberately narrow: a page
    # saying "competitive commissions" must not count as publishing one.
    "commission": re.compile(
        r"\b(commission|brokerage\s*(fee|rate|charge))\b[^.]{0,80}"
        r"(\d{1,2}(\.\d+)?\s*%|GH[¢C₵]|GHS)"
        r"|\b\d{1,2}(\.\d+)?\s*%\s*(commission|brokerage|per\s*trade)",
        re.I),
    # The more immediate barrier for a small saver.
    "minimum": re.compile(
        r"\bminimum\b[^.]{0,60}(GH[¢C₵]|GHS|cedi)"
        r"|\b(GH[¢C₵]|GHS)\s?[\d,]{3,}[^.]{0,40}\b(minimum|to\s*(open|start))",
        re.I),
    "account_open": re.compile(
        r"\b(open\s*an?\s*account|account\s*opening|ghana\s*card|"
        r"required\s*documents|kyc)\b", re.I),
    "online": re.compile(
        r"\b(online\s*trading|trade\s*online|mobile\s*app|trading\s*platform|"
        r"web\s*portal|self[\s-]*service)\b", re.I),
    "products": re.compile(
        r"\b(equit\w+|shares?|treasury\s*bills?|bonds?|ETFs?|"
        r"fixed\s*income|money\s*market)\b", re.I),
    # Marketing language WITHOUT a figure. Recorded separately so a site
    # saying "competitive rates" is not mistaken for one publishing them.
    "vague_pricing": re.compile(
        r"\b(competitive|attractive|favourable|favorable|best)\s+"
        r"(rates?|commissions?|fees?|pricing|charges)\b", re.I),
}


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
HDRS = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}


def providers() -> list[dict]:
    req = urllib.request.Request(
        BASE + "/providers?slug=like.broker-*&select=slug,trading_name,website",
        headers=HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            if "html" not in r.headers.get("Content-Type", "").lower():
                return 0, ""
            return getattr(r, "status", 200), r.read(500_000).decode(
                "utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:                                        # noqa: BLE001
        return 0, ""


def robots_allows(base: str) -> bool | None:
    status, txt = fetch(urllib.parse.urljoin(base, "/robots.txt"))
    if status != 200 or not txt:
        return None
    applies = blocked = False
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


def inner_links(html: str, base: str) -> list[str]:
    out: list[str] = []
    host = urllib.parse.urlparse(base).netloc
    for m in re.finditer(r'href=["\']([^"\']+)["\'][^>]*>(.{0,100}?)</a>',
                         html, re.I | re.S):
        href, label = m.group(1), strip_tags(m.group(2))
        if SKIP.search(href) or not LINK_HINT.search(f"{href} {label}"):
            continue
        full = urllib.parse.urljoin(base, href)
        if urllib.parse.urlparse(full).netloc != host:
            continue
        if full.rstrip("/") != base.rstrip("/") and full not in out:
            out.append(full)
        if len(out) >= 6:
            break
    return out


def scan(text: str) -> dict[str, bool]:
    return {k: bool(rx.search(text)) for k, rx in FIELD_SIGNALS.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="broker_terms_discovery.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.6)
    args = ap.parse_args()

    brokers = [b for b in providers() if (b.get("website") or "").startswith("http")]
    brokers.sort(key=lambda b: b["trading_name"] or "")
    if args.limit:
        brokers = brokers[: args.limit]
    print(f"Checking {len(brokers)} broker website(s)\n")

    rows = []
    for b in brokers:
        name = b["trading_name"] or b["slug"]
        base = (b["website"] or "").rstrip("/")
        blank = {k: "" for k in FIELD_SIGNALS}

        if robots_allows(base) is False:
            print(f"  {name[:30]:<32} robots.txt disallows — ask directly")
            rows.append({"broker": name, "website": base,
                         "status": "robots_disallow", "pages": 0,
                         "best_page": "", **blank})
            time.sleep(args.delay)
            continue

        status, home = fetch(base)
        if status != 200 or not home:
            print(f"  {name[:30]:<32} site unreachable")
            rows.append({"broker": name, "website": base,
                         "status": "unreachable", "pages": 0,
                         "best_page": "", **blank})
            time.sleep(args.delay)
            continue

        pages = inner_links(home, base) or [base + p for p in CANDIDATE_PATHS[1:6]]
        best: tuple[int, str, dict] | None = None
        # The home page counts too — some sites put everything on one page.
        checked = 1
        found_home = scan(strip_tags(home))
        best = (sum(found_home.values()), base, found_home)

        for url in pages[:6]:
            st, html = fetch(url)
            time.sleep(args.delay)
            if st != 200 or not html:
                continue
            checked += 1
            f = scan(strip_tags(html))
            if sum(f.values()) > best[0]:
                best = (sum(f.values()), url, f)

        score, url, found = best
        have = [k for k, v in found.items() if v and k != "vague_pricing"]
        note = ""
        if found.get("commission"):
            note = "  ← PUBLISHES A RATE"
        elif found.get("vague_pricing"):
            note = "  (says 'competitive' without a figure)"
        print(f"  {name[:30]:<32} {len(have)}/5  "
              f"{', '.join(have) or 'nothing'}{note}")
        rows.append({
            "broker": name, "website": base, "status": "checked",
            "pages": checked, "best_page": url,
            **{k: ("yes" if v else "no") for k, v in found.items()},
        })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    checked = [r for r in rows if r["status"] == "checked"]
    withrate = [r for r in checked if r.get("commission") == "yes"]
    withmin = [r for r in checked if r.get("minimum") == "yes"]
    vague = [r for r in checked if r.get("vague_pricing") == "yes"
             and r.get("commission") != "yes"]

    print(f"\n  {len(rows)} broker(s) -> {args.out}")
    print(f"    {len(checked)} reachable")
    print(f"    {len(withrate)} publish a commission rate")
    print(f"    {len(withmin)} publish a minimum to open an account")
    print(f"    {len(vague)} say 'competitive rates' without a figure")

    if withrate:
        print("\n  Publishing a rate:")
        for r in withrate:
            print(f"    {r['broker'][:34]:<36} {r['best_page'][:50]}")
        print("\n  Read those pages before publishing anything from them — a")
        print("  signal means the words appear near a figure, not that the")
        print("  figure is current or means what it looks like.")
    else:
        print("\n  None publishes a rate. That claim can now go on the broker")
        print("  page as something checked rather than assumed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

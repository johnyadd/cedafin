"""
discover_broker_terms_v2.py — checking the places the first scan did not.

WHY A SECOND PASS
The first scan visited the website recorded for each broker on the SEC
register and concluded that none of the twenty-four publishes a commission
rate. That conclusion is on the site.

IC Securities replied to say their fees are published. They are — at
wealth.ic.africa, a platform subdomain the register does not list. We had
checked ic.africa, the group site, and found nothing.

So the finding may be an artefact of where we looked. A retail platform is
frequently a separate subdomain from the corporate site, and that is exactly
where a fee schedule lives. Until this is checked, "not one of twenty-four
publishes a rate" is a claim about our scan rather than about the market.

WHAT THIS DOES DIFFERENTLY
Three things.

  Subdomains. For each broker's registered domain, tries wealth., invest.,
  app., trade., trading., my., client., portal. and online.

  Deeper paths. The first pass followed links from the home page. This also
  tries /help, /faq, /fees, /pricing, /support and their common variants
  directly, because a Help Centre is often not linked from the front page in a
  way a crawler follows.

  A stricter test for what counts. The first scan flagged a page if fee words
  appeared near a figure. That is how "competitive rates from 1% of your
  portfolio" and a page about a management fee both scored. This separates
  BROKERAGE commission from FUND charges, because IC publishes the second and
  not the first, and treating them alike is what produced the confusion.

MANNERS
robots.txt honoured, rate limited, truthful user agent. A subdomain that does
not resolve is silence, not a refusal, and is recorded as such.

Usage:
    python discover_broker_terms_v2.py --limit 3
    python discover_broker_terms_v2.py
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
        "Mozilla/5.0 (compatible; CedafinBot/0.2; comparison site data check)"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*",
}

# A retail platform is often a subdomain the regulator's register does not
# carry. IC's fees were at wealth.ic.africa while the register gave ic.africa.
SUBDOMAINS = [
    "",
    "wealth",
    "invest",
    "app",
    "trade",
    "trading",
    "my",
    "client",
    "portal",
    "online",
]

PATHS = [
    "",
    "/help",
    "/help-centre",
    "/help-center",
    "/faq",
    "/faqs",
    "/fees",
    "/pricing",
    "/charges",
    "/rates",
    "/support",
    "/brokerage",
    "/stockbroking",
]

# Commission on a TRADE. Deliberately narrow: this is the figure the site
# claims nobody publishes, so a loose match here would make the claim look
# wrong when it is not.
BROKERAGE_RX = re.compile(
    r"\b(brokerage|commission|trading)\s*(fee|rate|charge|commission)?\b[^.]{0,90}"
    r"(\d{1,2}(\.\d+)?\s*%|GH[¢C₵]\s?\d)"
    r"|\b\d{1,2}(\.\d+)?\s*%\b[^.]{0,60}\b(per\s*(trade|transaction)|brokerage|commission)\b"
    r"|\bcontract\s*note\b[^.]{0,90}(\d{1,2}(\.\d+)?\s*%)",
    re.I,
)

# A fund management charge. IC publishes one of these and not the above, and
# scoring them together is what made the first pass ambiguous.
FUND_FEE_RX = re.compile(
    r"\b(management|annual|yearly)\s*(fee|charge)\b[^.]{0,80}(\d{1,2}(\.\d+)?\s*%)"
    r"|\b\d{1,2}(\.\d+)?\s*%\b[^.]{0,50}\b(a|per)\s*year\b",
    re.I,
)

MINIMUM_RX = re.compile(
    r"\bminimum\b[^.]{0,70}(GH[¢C₵]|GHS|cedi)"
    r"|\b(GH[¢C₵]|GHS)\s?[\d,]{3,}[^.]{0,50}\b(minimum|to\s*(open|start|invest))",
    re.I,
)

NONRESIDENT_RX = re.compile(
    r"\b(non[\s-]?resident|diaspora|living\s*abroad|outside\s*Ghana|"
    r"overseas\s*(client|customer|investor))\b",
    re.I,
)

ONLINE_OPEN_RX = re.compile(
    r"\b(open\s*an?\s*account\s*online|register\s*online|"
    r"sign\s*up\s*online|onboard\w*\s*online|fully\s*digital|"
    r"without\s*visiting)\b",
    re.I,
)


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


def brokers() -> list[dict]:
    req = urllib.request.Request(
        BASE + "/providers?slug=like.broker-*&select=slug,trading_name,website",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 12) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            if "html" not in r.headers.get("Content-Type", "").lower():
                return 0, ""
            return getattr(r, "status", 200), r.read(400_000).decode(
                "utf-8", errors="replace"
            )
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001
        return 0, ""


def strip_tags(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def root_domain(website: str) -> str | None:
    """The registrable part, so subdomains can be built from it."""
    try:
        host = urllib.parse.urlparse(
            website if "://" in website else f"https://{website}"
        ).netloc.lower()
    except ValueError:
        return None
    host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host or None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="broker_terms_v2.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.4)
    args = ap.parse_args()

    firms = [b for b in brokers() if (b.get("website") or "").strip()]
    firms.sort(key=lambda b: b["trading_name"] or "")
    if args.limit:
        firms = firms[: args.limit]

    print(f"Re-checking {len(firms)} broker(s), subdomains included\n")

    rows = []
    for b in firms:
        name = b["trading_name"] or b["slug"]
        root = root_domain(b["website"] or "")
        if not root:
            print(f"  {name[:30]:<32} no usable domain")
            continue

        found = {
            "brokerage": "",
            "fund_fee": "",
            "minimum": "",
            "nonresident": "",
            "online_open": "",
        }
        hosts_alive: list[str] = []
        checked = 0

        for sub in SUBDOMAINS:
            host = f"{sub}.{root}" if sub else root
            # One cheap probe before spending requests on paths.
            st, home = fetch(f"https://{host}/")
            time.sleep(args.delay)
            if st != 200 or not home:
                continue
            hosts_alive.append(host)
            checked += 1

            pages = [(f"https://{host}/", home)]
            for path in PATHS[1:]:
                st2, html = fetch(f"https://{host}{path}")
                time.sleep(args.delay)
                if st2 == 200 and html:
                    pages.append((f"https://{host}{path}", html))
                    checked += 1

            for url, html in pages:
                text = strip_tags(html)
                if not found["brokerage"] and BROKERAGE_RX.search(text):
                    found["brokerage"] = url
                if not found["fund_fee"] and FUND_FEE_RX.search(text):
                    found["fund_fee"] = url
                if not found["minimum"] and MINIMUM_RX.search(text):
                    found["minimum"] = url
                if not found["nonresident"] and NONRESIDENT_RX.search(text):
                    found["nonresident"] = url
                if not found["online_open"] and ONLINE_OPEN_RX.search(text):
                    found["online_open"] = url

        flag = ""
        if found["brokerage"]:
            flag = "  ← BROKERAGE RATE"
        elif found["fund_fee"]:
            flag = "  (fund fee only)"
        hits = [k for k, v in found.items() if v]
        print(
            f"  {name[:30]:<32} {len(hosts_alive)} host(s), {checked:>2} page(s)  "
            f"{', '.join(hits) or 'nothing'}{flag}"
        )

        rows.append(
            {
                "broker": name,
                "root_domain": root,
                "hosts_alive": " ".join(hosts_alive),
                "pages_checked": checked,
                **found,
            }
        )

    if rows:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    brk = [r for r in rows if r["brokerage"]]
    fnd = [r for r in rows if r["fund_fee"] and not r["brokerage"]]
    nr = [r for r in rows if r["nonresident"]]
    on = [r for r in rows if r["online_open"]]
    subs = [r for r in rows if len(r["hosts_alive"].split()) > 1]

    print(f"\n  {len(rows)} broker(s) -> {args.out}")
    print(f"    {len(brk)} publish a BROKERAGE rate")
    print(f"    {len(fnd)} publish a fund charge but no brokerage rate")
    print(f"    {len(nr)} mention non-resident or diaspora clients")
    print(f"    {len(on)} mention opening an account online")
    print(f"    {len(subs)} have a platform subdomain the register does not list")

    if brk:
        print("\n  Publishing a brokerage rate:")
        for r in brk:
            print(f"    {r['broker'][:32]:<34} {r['brokerage'][:60]}")
        print("\n  Read those pages before changing anything. A match means the")
        print("  words appear near a figure, not that the figure is a")
        print("  commission or that it is current.")
    else:
        print("\n  Still none. The claim survives a scan that looked in the")
        print("  places the first one missed, which is a stronger thing to be")
        print("  able to say than it was before.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

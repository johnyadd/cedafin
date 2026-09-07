"""
discover_savings_loans.py — do any of them publish what they charge?

WHY THIS MATTERS MORE THAN THE BROKER SCAN DID
Bank of Ghana publishes a monthly APR table for banks. It publishes no
equivalent for savings and loans companies, so a business refused by a bank
cannot compare what the alternatives cost.

If some of these twenty-six publish rates on their own sites, that is a
comparison nobody in Ghana has assembled. If none does, then the gap this site
already names on its funding page is larger than we said — it is not that BoG
does not publish for them, it is that nobody does.

Either answer is worth having, which is why this runs before anything is
built.

TWO LESSONS FROM EARLIER SCANS, BUILT IN
The broker scan concluded that nobody published a commission rate, and a
broker then pointed out we had checked their corporate site rather than their
lending platform. So this checks subdomains and the paths where a rate would
live, not just the home page.

And the private funds scan taught the value of separating what looks like a
match from what is one. A regex hit means the words appeared near a figure; it
does not mean the figure is a lending rate. Every match is printed for reading
rather than counted and trusted.

WHAT IT LOOKS FOR
  rate       — an interest rate or APR on a loan product
  fees       — arrangement, processing or facility charges
  minimum    — the smallest loan they will make
  apply      — whether a business that knows nobody can start an application

The last is not a rate but it is the practical question. A lender whose site
has no application route is not reachable by somebody who does not already
bank with them.

Usage:
    python discover_savings_loans.py --limit 3
    python discover_savings_loans.py
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

SUBDOMAINS = ["", "www"]

PATHS = [
    "",
    "/loans",
    "/products",
    "/personal",
    "/business",
    "/sme",
    "/rates",
    "/interest-rates",
    "/fees",
    "/charges",
    "/tariff",
    "/tariffs",
    "/faq",
    "/faqs",
    "/apply",
    "/loan-calculator",
]

# A lending rate. Deliberately narrow — the point is to find what a borrower
# would pay, not any percentage on the page.
RATE_RX = re.compile(
    r"\b(interest|lending|loan|apr|annual\s+percentage)\s*(rate|charge)?\b"
    r"[^.]{0,90}(\d{1,3}(\.\d+)?\s*%)"
    r"|(\d{1,3}(\.\d+)?\s*%)[^.]{0,60}\b(per\s+(month|annum|year)|p\.?a\.?|"
    r"monthly|flat\s+rate|reducing\s+balance)\b",
    re.I,
)

FEE_RX = re.compile(
    r"\b(processing|arrangement|facility|commitment|application|"
    r"administrative)\s*(fee|charge)\b[^.]{0,80}"
    r"(\d{1,3}(\.\d+)?\s*%|GH[¢C₵]\s?[\d,]+)",
    re.I,
)

MINIMUM_RX = re.compile(
    r"\b(minimum|from|as\s+low\s+as|starting\s+(at|from))\b[^.]{0,60}"
    r"(GH[¢C₵]|GHS)\s?[\d,]{3,}"
    r"|(GH[¢C₵]|GHS)\s?[\d,]{3,}[^.]{0,50}\b(minimum|and\s+above)\b",
    re.I,
)

APPLY_RX = re.compile(
    r"\b(apply\s+(now|online|for)|loan\s+application|start\s+your\s+"
    r"application|application\s+form)\b",
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


def firms() -> list[dict]:
    req = urllib.request.Request(
        BASE + "/providers?slug=like.sl-*&select=slug,trading_name,website",
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


def strip_tags(html_text: str) -> str:
    html_text = re.sub(
        r"<(script|style)\b.*?</\1>", " ", html_text, flags=re.I | re.S
    )
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_text))


def root(url: str) -> str | None:
    try:
        host = urllib.parse.urlparse((url or "").strip()).netloc.lower()
    except ValueError:
        return None
    host = host.split(":")[0]
    return host[4:] if host.startswith("www.") else host or None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="savings_loans_discovery.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.4)
    args = ap.parse_args()

    all_firms = [f for f in firms() if (f.get("website") or "").strip()]
    all_firms.sort(key=lambda f: f["trading_name"] or "")
    if args.limit:
        all_firms = all_firms[: args.limit]

    print(f"Checking {len(all_firms)} savings and loans company website(s)\n")
    rows = []

    for f in all_firms:
        name = f["trading_name"] or f["slug"]
        host_root = root(f["website"])
        if not host_root:
            print(f"  {name[:40]:<42} no usable domain")
            continue

        found = {"rate": "", "fees": "", "minimum": "", "apply": ""}
        pages = 0
        alive = False

        for sub in SUBDOMAINS:
            host = f"{sub}.{host_root}" if sub else host_root
            st, home = fetch(f"https://{host}/")
            time.sleep(args.delay)
            if st != 200 or not home:
                continue
            alive = True

            docs = [home]
            for path in PATHS[1:]:
                st2, page = fetch(f"https://{host}{path}")
                time.sleep(args.delay)
                if st2 == 200 and page:
                    docs.append(page)
            pages = len(docs)

            for page in docs:
                text = strip_tags(page)
                if not found["rate"]:
                    m = RATE_RX.search(text)
                    if m:
                        found["rate"] = m.group(0)[:130].strip()
                if not found["fees"]:
                    m = FEE_RX.search(text)
                    if m:
                        found["fees"] = m.group(0)[:130].strip()
                if not found["minimum"]:
                    m = MINIMUM_RX.search(text)
                    if m:
                        found["minimum"] = m.group(0)[:100].strip()
                if not found["apply"]:
                    m = APPLY_RX.search(text)
                    if m:
                        found["apply"] = m.group(0)
            break

        hits = [k for k, v in found.items() if v]
        flag = "  <- RATE" if found["rate"] else ""
        print(
            f"  {name[:40]:<42} {'live' if alive else 'DEAD':<5} "
            f"{pages:>2}p  {', '.join(hits) or 'nothing'}{flag}"
        )

        rows.append(
            {
                "company": name,
                "domain": host_root,
                "alive": "yes" if alive else "no",
                "pages": pages,
                **found,
            }
        )

    if rows:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    live = [r for r in rows if r["alive"] == "yes"]
    rate = [r for r in rows if r["rate"]]
    mins = [r for r in rows if r["minimum"]]

    print(f"\n  {len(rows)} checked -> {args.out}")
    print(f"    {len(live)} with a working website")
    print(f"    {len(rate)} publishing something that looks like a rate")
    print(f"    {len(mins)} publishing a minimum loan")
    print()

    if rate:
        print("  Read every one of these before using it. A match means the")
        print("  words appeared near a figure — not that the figure is a")
        print("  lending rate, nor that it is current:")
        print()
        for r in rate:
            print(f"    {r['company'][:34]:<36} {r['rate'][:70]}")
        print()
        print("  If several hold up, this is a comparison nobody in Ghana has")
        print("  assembled — Bank of Ghana publishes an APR table for banks and")
        print("  nothing equivalent for these.")
    else:
        print("  None found. That makes the gap larger than our funding page")
        print("  says: it is not that the regulator does not publish rates for")
        print("  these lenders, it is that nobody does. Worth saying plainly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

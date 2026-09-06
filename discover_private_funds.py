"""
discover_private_funds.py — is there enough to build a page on?

WHY THIS RUNS BEFORE ANYTHING IS BUILT
The SEC register lists nine licensed private funds and gives their names and
websites. Nothing else — no ticket size, no stage, no sector, no terms.

A business owner considering equity finance needs exactly those things, and
none of them is in the register. So the question is whether the firms publish
them, and that has to be answered before a page is designed around them.

The broker scan taught this the expensive way. It concluded that nobody
publishes a commission rate, and a broker then pointed out we had been looking
at their corporate site rather than their platform. So this checks subdomains
and the obvious paths, not just the home page.

WHAT IT LOOKS FOR
Four things, each of which a business owner would want before making contact:

  ticket size    — how much they invest, in cedis or dollars
  stage          — seed, early, growth, expansion, buyout
  sector         — where they invest, if they say
  how to apply   — whether there is a route in for an unintroduced founder

The last one matters most and is usually missing. A fund with no published
application route is not reachable by a business that does not already know
somebody, which is a fact worth publishing whether or not the fund likes it.

WHAT IT DELIBERATELY DOES NOT DO
Judge. A private fund with no public application process is behaving normally
for its asset class; venture capital is a relationship business. The scan
records what is published, and the page — if there is one — should say that
plainly rather than treating it as a failing.

Usage:
    python discover_private_funds.py --limit 2
    python discover_private_funds.py
"""

from __future__ import annotations

import argparse
import csv
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
    "/about",
    "/investments",
    "/portfolio",
    "/our-approach",
    "/approach",
    "/what-we-do",
    "/criteria",
    "/investment-criteria",
    "/apply",
    "/for-entrepreneurs",
    "/entrepreneurs",
    "/funding",
    "/contact",
]

# A cheque size, in either currency, near words that mean investment.
TICKET_RX = re.compile(
    r"(?:invest|ticket|cheque|check|deploy|commitment|funding)[^.]{0,80}"
    r"(?:US\$|USD|\$|GH[¢C₵]|GHS)\s?[\d,.]+\s?(?:k|m|million|thousand)?"
    r"|(?:US\$|USD|\$|GH[¢C₵]|GHS)\s?[\d,.]+\s?(?:k|m|million|thousand)?"
    r"[^.]{0,60}(?:per\s+(?:company|investment|deal)|ticket|investment\s+size)",
    re.I,
)

STAGE_RX = re.compile(
    r"\b(seed|pre-seed|early[\s-]stage|series\s+[ab]|growth[\s-]stage|"
    r"expansion|buyout|mezzanine|late[\s-]stage|start-?ups?)\b",
    re.I,
)

SECTOR_RX = re.compile(
    r"\b(agribusiness|agriculture|fintech|healthcare|education|manufacturing|"
    r"renewable|clean\s?energy|logistics|technology|ict|consumer\s+goods|"
    r"financial\s+services|real\s+estate|mining)\b",
    re.I,
)

# The one that matters: can a founder who knows nobody get in touch?
APPLY_RX = re.compile(
    r"\b(apply|application|submit\s+(?:your|a)\s+(?:pitch|deck|business|"
    r"proposal)|pitch\s+(?:deck|us)|send\s+us\s+your|funding\s+request|"
    r"get\s+funded|raise\s+with\s+us)\b",
    re.I,
)

FIRMS: list[tuple[str, str]] = [
    ("Ci GABA VC LTD", "https://www.siaghana.com"),
    ("Growth Investment Partners Ghana LTD", "https://www.gipghana.com"),
    ("Injaro Ghana Venture Capital Fund", "https://www.injaroinvestments.com"),
    ("ISF Ghana Venture Capital LTD", "http://www.impcapadv.com/"),
    ("Mirepa Capital SME Fund 1 Limited", "https://www.mirepaglobal.com"),
    ("Oasis Africa VC Fund II LTD", "https://www.oasiscapitalghana.com"),
    ("Oasis Africa VC Fund Ltd", "https://www.oasiscapitalghana.com"),
    # The register gives "https://  ashfieldinvest.com" — two spaces, and a
    # domain that does not match the fund name. Recorded as the register has
    # it, cleaned only of the whitespace, and flagged in the output.
    ("Origen Private Debt Fund LTD", "https://ashfieldinvest.com"),
    ("Wangara Green Venture Capital Co. Ltd", "https://www.wangaracapital.com"),
]


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


def root(url: str) -> str | None:
    try:
        host = urllib.parse.urlparse(url.strip()).netloc.lower()
    except ValueError:
        return None
    host = host.split(":")[0]
    return host[4:] if host.startswith("www.") else host or None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="private_funds_discovery.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.4)
    args = ap.parse_args()

    seen_hosts: set[str] = set()
    firms = FIRMS[: args.limit] if args.limit else FIRMS

    print(f"Checking {len(firms)} licensed private fund(s)\n")
    rows = []

    for name, site in firms:
        host_root = root(site)
        if not host_root:
            print(f"  {name[:36]:<38} no usable domain in the register")
            rows.append({"fund": name, "domain": "", "alive": "no"})
            continue

        # Two funds share a site. Fetch once, report for both.
        cached = host_root in seen_hosts
        seen_hosts.add(host_root)

        found = {"ticket": "", "stage": "", "sector": "", "apply": ""}
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
                st2, html = fetch(f"https://{host}{path}")
                time.sleep(args.delay)
                if st2 == 200 and html:
                    docs.append(html)
            pages = len(docs)

            for html in docs:
                text = strip_tags(html)
                if not found["ticket"]:
                    m = TICKET_RX.search(text)
                    if m:
                        found["ticket"] = m.group(0)[:120].strip()
                if not found["stage"]:
                    m = STAGE_RX.search(text)
                    if m:
                        found["stage"] = m.group(0)
                if not found["sector"]:
                    m = SECTOR_RX.search(text)
                    if m:
                        found["sector"] = m.group(0)
                if not found["apply"]:
                    m = APPLY_RX.search(text)
                    if m:
                        found["apply"] = m.group(0)
            break

        hits = [k for k, v in found.items() if v]
        note = " (shared site)" if cached else ""
        print(
            f"  {name[:36]:<38} {'live' if alive else 'DEAD':<5} "
            f"{pages:>2}p  {', '.join(hits) or 'nothing'}{note}"
        )

        rows.append(
            {
                "fund": name,
                "domain": host_root,
                "alive": "yes" if alive else "no",
                "pages": pages,
                **found,
            }
        )

    if rows:
        keys = sorted({k for r in rows for k in r})
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)

    live = [r for r in rows if r.get("alive") == "yes"]
    ticket = [r for r in rows if r.get("ticket")]
    apply_ = [r for r in rows if r.get("apply")]

    print(f"\n  {len(rows)} fund(s) -> {args.out}")
    print(f"    {len(live)} with a working website")
    print(f"    {len(ticket)} publishing anything resembling a ticket size")
    print(f"    {len(apply_)} with a visible way for a founder to make contact")
    print()
    if len(ticket) < 3:
        print("  Not enough published detail to build a comparison on. What")
        print("  there IS to say is that Ghana has nine licensed private funds")
        print("  and almost none of them tells a business owner what they")
        print("  invest, at what stage, or how to reach them — which is a")
        print("  finding for the borrowing side rather than a page of its own.")
    else:
        print("  Enough to build something. Read the matches before using them:")
        print("  a regex hit means the words appeared near a figure, not that")
        print("  the figure means what it looks like.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

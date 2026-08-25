"""
fetch_bog_registers.py — every licensed lender in Ghana, from the regulator.

WHAT THIS GETS YOU
Bank of Ghana publishes a register per institution type: banks, savings and
loans, microfinance, microcredit, financial NGOs, community banks, development
finance, and — the one that matters most for SMEs — entities licensed to
provide DIGITAL LENDING services, which is where Fido, Carbon and the rest sit.

Each is a plain server-rendered HTML table: name, address, phone, fax, website,
email. No JavaScript, no pagination. The savings and loans register alone lists
26 companies with 24 websites between them.

That makes the borrowing side better served than the investment side was. The
SEC register gave 152 licensees and it took a day to find five funds with
usable data. Here the regulator publishes a monthly APR report for the bank
tier AND a register covering every other tier.

TWO THINGS THAT WILL DATE THIS DATA

  THE SECTOR IS MID-RESTRUCTURE. BoG's revised microfinance framework
  (January 2026) replaces the old four-tier system with four new institutional
  categories, and every existing institution must transition by 31 December
  2026. Names, categories and licences will move. Anything captured now needs
  re-checking, and any page must show the date it was taken.

  A REGISTER ENTRY IS NOT AN ENDORSEMENT. It says an institution was licensed
  when the page was published. It says nothing about whether it is solvent,
  lending, or still trading — Ghana's microfinance sector has a history of
  collapses. The same rule as licence_status.ts on the SEC side: report what
  the regulator states, never paraphrase it into a judgement.

DISCOVERY, NOT GUESSWORK
The register URLs are found by reading the index page rather than assumed.
Guessing paths has cost more rounds on this project than reading a page ever
has.

Usage:
    python fetch_bog_registers.py --list      # find the registers
    python fetch_bog_registers.py             # scrape them to CSV
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.bog.gov.gh"
INDEXES = [
    f"{BASE}/supervision-regulation/all-institutions/",
    f"{BASE}/supervision-regulation/registered-institutions/",
    f"{BASE}/supervision-regulation/ofisd/list-of-ofis/",
]

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*",
}

# Only follow links that look like an institution register.
REGISTER_HINTS = re.compile(
    r"bank|savings|loans|microfinance|microcredit|ngo|forex|community|"
    r"credit-bureau|development-finance|digital-lend|finance-house|"
    r"rural|psp|payment-service",
    re.I,
)

SKIP = re.compile(r"unclaimed|notice|news|speech|career|contact|sitemap|"
                  r"cookie|legal|policy|holiday|report|guideline", re.I)


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def get(url: str, timeout: int = 40) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:                                   # noqa: BLE001
        print(f"    {type(e).__name__}: {str(e)[:80]}")
        return ""


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def find_registers(page: str, seen: set[str]) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page,
                         re.I | re.S):
        href, label = m.group(1), strip_tags(m.group(2))
        if not href.startswith("http"):
            href = urllib.parse.urljoin(BASE, href)
        if not href.startswith(BASE) or href in seen:
            continue
        if SKIP.search(href) or not REGISTER_HINTS.search(href):
            continue
        if not re.search(r"supervision-regulation", href):
            continue
        seen.add(href)
        out.append((label or href.rstrip("/").rsplit("/", 1)[-1], href))
    return out


def parse_table(page: str) -> tuple[list[str], list[list[str]]]:
    """
    One plain <table> per register. The header row is repeated as the first
    body row on these pages, so a row identical to the header is dropped.
    """
    tables = re.findall(r"<table\b.*?</table>", page, re.I | re.S)
    if not tables:
        return [], []
    # The register is the largest table on the page; the rest are layout.
    table = max(tables, key=len)

    rows: list[list[str]] = []
    for tr in re.findall(r"<tr\b.*?</tr>", table, re.I | re.S):
        cells = [strip_tags(c) for c in
                 re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, re.I | re.S)]
        if any(c for c in cells):
            rows.append(cells)
    if not rows:
        return [], []

    header = rows[0]
    body = [r for r in rows[1:] if r != header]
    return header, body


def title_of(page: str) -> str:
    m = re.search(r"<title>(.*?)</title>", page, re.I | re.S)
    return strip_tags(m.group(1)).split("–")[0].strip() if m else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="bog_lenders.csv")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    print("Finding registers\n")
    seen: set[str] = set()
    registers: list[tuple[str, str]] = []
    for idx in INDEXES:
        page = get(idx)
        if not page:
            print(f"  {idx} — unreachable")
            continue
        found = find_registers(page, seen)
        print(f"  {idx.rsplit('/', 2)[-2]}: {len(found)} link(s)")
        registers += found
        time.sleep(args.delay)

    if not registers:
        print("\nNo register links found. Open this in a browser and paste a")
        print(f"register URL: {INDEXES[0]}")
        return 1

    print(f"\n{len(registers)} register(s):")
    for label, url in registers:
        print(f"  {label[:44]:<46} {url.replace(BASE, '')}")

    if args.list:
        print("\nList only — nothing scraped.")
        return 0

    print()
    all_rows: list[dict] = []
    for label, url in registers:
        page = get(url)
        if not page:
            continue
        header, body = parse_table(page)
        if not body:
            print(f"  {label[:40]:<42} no table")
            time.sleep(args.delay)
            continue

        category = title_of(page) or label
        # Map whatever columns exist onto a common shape.
        idx_of = {}
        for i, h in enumerate(header):
            k = h.lower()
            if "name" in k:
                idx_of.setdefault("name", i)
            elif "address" in k:
                idx_of.setdefault("address", i)
            elif "phone" in k or "tel" in k:
                idx_of.setdefault("phone", i)
            elif "website" in k or "web" in k:
                idx_of.setdefault("website", i)
            elif "email" in k or "e-mail" in k:
                idx_of.setdefault("email", i)
        idx_of.setdefault("name", 0)

        n = 0
        for row in body:
            def cell(key: str) -> str:
                i = idx_of.get(key)
                return row[i] if i is not None and i < len(row) else ""
            name = cell("name")
            if not name or len(name) < 3:
                continue
            all_rows.append({
                "category": category,
                "name": name,
                "address": cell("address"),
                "phone": cell("phone"),
                "website": cell("website"),
                "email": cell("email"),
                "register_url": url,
            })
            n += 1
        print(f"  {label[:40]:<42} {n:>4} institution(s)")
        time.sleep(args.delay)

    if not all_rows:
        print("\nNothing extracted.")
        return 1

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    by_cat: dict[str, int] = {}
    with_site = 0
    for r in all_rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
        if r["website"].startswith("http"):
            with_site += 1

    print(f"\n  {len(all_rows)} institutions -> {args.out}")
    for cat, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>4}  {cat[:56]}")
    print(f"\n  {with_site} have a website on file — the starting point for")
    print("  finding who publishes rates.")
    print("\n  A register entry means LICENSED WHEN PUBLISHED. It does not mean")
    print("  solvent, lending, or still trading. The microfinance sector is")
    print("  mid-restructure with a transition deadline of 31 December 2026.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

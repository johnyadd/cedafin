"""
discover.py — Phase 0 provider data discovery.

Automates the mechanical part of "which Ghanaian providers actually publish
usable price data". For each provider it:

  1. fetches the site and finds candidate pages (prices, NAV, factsheets, PDFs)
  2. fetches the best candidates and looks for price-shaped and date-shaped text
  3. queries the Wayback Machine CDX API for snapshot history

Step 3 is the important one. You cannot tell from a single fetch whether a page
showing "GH2 1.2345" updates daily or has been frozen since 2023. Wayback gives
you every archived snapshot with a content digest, so a page with 300 snapshots
and constantly-changing digests is live, and one with 12 identical digests is
static. That turns cadence from a judgement call into a query.

WHAT THIS CANNOT DO — and why you still open the top candidates by eye:
  - decide whether a number is a fund NAV, a share price, or a worked example
  - tell a TER from a management fee
  - see anything behind a login, or available only on request
  - read a price printed inside an image
Expect it to save roughly two thirds of the work, not all of it.

Usage (from the repo root, with the engine venv active):
    python discover.py                 # uses the built-in provider list
    python discover.py --out disc.csv  # writes a CSV to fill in by hand

Standard library only — nothing to install.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 25
CDX_TIMEOUT = 75          # the CDX API is genuinely slow; 20s was far too short

BROWSER_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Connection": "close",
}

# Confirm every one of these against licensees.sec.gov.gh before relying on it.
# This list exists to start the search, not to be authoritative.
PROVIDERS: list[tuple[str, str]] = [
    ("Databank", "https://www.databankgroup.com"),
    ("Fidelity Securities (Fidelity Bank Ghana)", "https://www.fidelitybank.com.gh"),
    ("IC Asset Managers", "https://www.ic.africa"),
    ("EDC Investments", "https://www.edcinvestments.com"),
    ("Galaxy Capital", "https://www.galaxycapitalgh.com"),
    ("Republic Investments Ghana", "https://www.republicghana.com"),
    ("NTHC", "https://www.nthcghana.com"),
    ("Petra Trust / Petra Advisory", "https://www.petratrust.com"),
    ("Stanbic Investment Management", "https://www.stanbicbank.com.gh"),
    ("Black Star Group", "https://blackstargroup.ai"),
]

# Link text / href fragments that suggest a price or performance page.
CANDIDATE_HINTS = [
    "unit price", "unit-price", "prices", "price", "nav", "net asset",
    "fact sheet", "factsheet", "fact-sheet", "performance", "fund",
    "mutual fund", "unit trust", "returns", "yield", "downloads",
    "reports", "publications", "investor",
]

# Anything matching these is worth flagging even without helpful link text.
PDF_HINTS = ["factsheet", "fact-sheet", "fund", "performance", "report", "price"]

DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
]
# A unit price looks like 1.2345 / 2.87 / 0.9812 — 1-4 decimals, small integer part.
PRICE_PATTERN = r"\b\d{1,3}\.\d{2,6}\b"
# A yield looks like 18.75% or 18.75 percent.
YIELD_PATTERN = r"\b\d{1,2}\.\d{1,2}\s*%"


def _ctx() -> ssl.SSLContext:
    """Some Ghanaian hosts have incomplete chains. Research fetch, not a payment."""
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


class _Redirect(urllib.request.HTTPRedirectHandler):
    """Follow 307/308 as well as 301/302/303, and remember the final URL."""

    def __init__(self) -> None:
        self.final: str | None = None

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.final = newurl
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, limit: int = 400_000, timeout: int = TIMEOUT) -> tuple[int, str]:
    """Returns (status, body). Status 0 means a transport error; body carries it."""
    handler = _Redirect()
    opener = urllib.request.build_opener(
        handler, urllib.request.HTTPSHandler(context=_ctx()))
    req = urllib.request.Request(url, headers=BROWSER_HEADERS)
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read(limit)
            enc = r.headers.get_content_charset() or "utf-8"
            return getattr(r, "status", 200), raw.decode(enc, errors="replace")
    except urllib.error.HTTPError as e:
        hint = ""
        if e.code in (403, 503, 530):
            hint = " (bot protection or origin down — open it in a browser)"
        elif e.code in (307, 308):
            loc = e.headers.get("Location", "")
            hint = f" (redirect to {loc})" if loc else ""
        return e.code, f"__ERROR__ HTTP {e.code}{hint}"
    except Exception as e:                                   # noqa: BLE001
        kind = type(e).__name__
        hint = ""
        if "getaddrinfo" in str(e):
            hint = " (domain does not resolve — the URL in PROVIDERS is wrong)"
        elif "timed out" in str(e).lower():
            hint = " (timed out — try again, or the host is slow from here)"
        return 0, f"__ERROR__ {kind}: {e}{hint}"


def find_links(html: str, base: str) -> list[tuple[str, str]]:
    """Return (text, absolute_url) for anchors whose text or href looks relevant."""
    out: dict[str, tuple[str, str]] = {}
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         html, re.I | re.S):
        href, text = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        text = re.sub(r"\s+", " ", text).strip().lower()
        absolute = urllib.parse.urljoin(base, href)
        if not absolute.startswith("http"):
            continue
        hay = (text + " " + href).lower()
        is_pdf = absolute.lower().endswith(".pdf")
        hit = any(h in hay for h in CANDIDATE_HINTS)
        if is_pdf:
            hit = hit or any(h in hay for h in PDF_HINTS)
        if hit:
            out[absolute] = (text[:60], absolute)
    return list(out.values())


def wayback_cadence(url: str) -> dict:
    """
    Snapshot history from the Wayback CDX API.

    THE KEY SIGNAL: distinct content digests over time. Many snapshots with many
    distinct digests means the page changes; many snapshots with one digest
    means it is frozen. That is publication cadence, observed rather than
    guessed.
    """
    q = urllib.parse.urlencode({
        "url": url, "output": "json", "fl": "timestamp,digest",
        "limit": "400", "collapse": "digest",
    })
    # Two attempts: CDX frequently times out or 503s on first contact.
    body = ""
    status = 0
    for attempt in range(2):
        status, body = fetch(f"https://web.archive.org/cdx/search/cdx?{q}",
                             limit=200_000, timeout=CDX_TIMEOUT)
        if status == 200 and not body.startswith("__ERROR__"):
            break
        time.sleep(3)
    if status != 200 or body.startswith("__ERROR__"):
        detail = body[9:120] if body.startswith("__ERROR__") else f"HTTP {status}"
        return {"snapshots": 0, "distinct": 0, "first": "", "last": "",
                "note": f"cdx failed: {detail}"}
    if not body.strip():
        return {"snapshots": 0, "distinct": 0, "first": "", "last": "",
                "note": "never archived"}
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return {"snapshots": 0, "distinct": 0, "first": "", "last": "", "note": "cdx parse failed"}
    if len(rows) < 2:
        return {"snapshots": 0, "distinct": 0, "first": "", "last": "", "note": "never archived"}

    data = rows[1:]                       # row 0 is the header
    stamps = sorted(r[0] for r in data)
    distinct = len({r[1] for r in data})
    first, last = stamps[0][:8], stamps[-1][:8]

    note = ""
    if distinct <= 2 and len(data) > 5:
        note = "LOOKS STATIC — many snapshots, almost no content change"
    elif distinct >= 20:
        note = "changes often"
    return {"snapshots": len(data), "distinct": distinct,
            "first": first, "last": last, "note": note}


@dataclass
class ProviderResult:
    provider: str
    site: str
    site_status: int = 0
    candidates: list[str] = field(default_factory=list)
    best_url: str = ""
    has_prices: bool = False
    has_yield: bool = False
    dates_found: str = ""
    pdf_count: int = 0
    wayback: dict = field(default_factory=dict)
    error: str = ""


def probe(url: str) -> dict:
    """Look for price-shaped and date-shaped content on one page."""
    status, html = fetch(url)
    if status != 200 or html.startswith("__ERROR__"):
        return {"ok": False}
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    dates: list[str] = []
    for p in DATE_PATTERNS:
        dates += re.findall(p, text, re.I)
    return {
        "ok": True,
        "prices": len(re.findall(PRICE_PATTERN, text)),
        "yields": len(re.findall(YIELD_PATTERN, text)),
        "dates": sorted(set(dates))[:4],
    }


def investigate(name: str, site: str, skip_wayback: bool = False) -> ProviderResult:
    res = ProviderResult(provider=name, site=site)
    status, html = fetch(site)
    res.site_status = status
    if status != 200 or html.startswith("__ERROR__"):
        res.error = html[:120] if html.startswith("__ERROR__") else f"HTTP {status}"
        return res

    links = find_links(html, site)
    res.pdf_count = sum(1 for _, u in links if u.lower().endswith(".pdf"))
    res.candidates = [u for _, u in links][:12]

    # Prefer a page whose URL mentions price or NAV, else the first candidate.
    ranked = sorted(
        res.candidates,
        key=lambda u: (0 if re.search(r"price|nav|unit", u, re.I) else 1,
                       0 if not u.lower().endswith(".pdf") else 1),
    )
    for url in ranked[:3]:
        if url.lower().endswith(".pdf"):
            continue
        p = probe(url)
        if p.get("ok") and (p["prices"] > 3 or p["yields"] > 1):
            res.best_url = url
            res.has_prices = p["prices"] > 3
            res.has_yield = p["yields"] > 1
            res.dates_found = "; ".join(p["dates"])
            break

    if not skip_wayback:
        res.wayback = wayback_cadence(res.best_url or site)
    return res


# ---------------------------------------------------------------------------
# SEC licensee register
#
# The built-in PROVIDERS list is from memory and two of its URLs do not resolve.
# The register is the authoritative source for who is licensed and often carries
# the website too. Run --sec first, then work from sec_licensees.csv.
#
# No API exists; these are server-rendered PHP pages, one per operator type,
# which is why a deterministic parse is possible at all.
# ---------------------------------------------------------------------------

SEC_PAGES = [
    ("Fund Managers", "https://licensees.sec.gov.gh/licensees/FundManager.php"),
    ("Mutual Funds", "https://licensees.sec.gov.gh/licensees/MutualFunds.php"),
    ("Exchange Traded Funds", "https://licensees.sec.gov.gh/licensees/ExchangeTradedFunds.php"),
    ("Private Funds", "https://licensees.sec.gov.gh/licensees/PrivateFunds.php"),
    ("Registrars", "https://licensees.sec.gov.gh/licensees/Registrars.php"),
    ("Securities Exchanges", "https://licensees.sec.gov.gh/licensees/SecuritiesExchanges.php"),
]


def strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def scrape_sec(out_path: str) -> int:
    """
    Pull the licensee register into a CSV.

    NOTE ON THE STATUS FLAG: the register marks some licensees as having
    regulatory issues. The SEC has said publicly that this is NOT a list of
    firms unsafe to invest with, and that reading it that way is wrong. This
    script records the raw cell text only. Render it verbatim via
    lib/compliance/licence-status.ts — never paraphrased.
    """
    rows: list[list[str]] = []
    for category, url in SEC_PAGES:
        print(f"\n=== SEC register: {category} ===", flush=True)
        status, html = fetch(url)
        if status != 200 or html.startswith("__ERROR__"):
            print(f"  FAILED: {html[9:140] if html.startswith('__ERROR__') else status}")
            continue

        found = 0
        for tr in re.findall(r"<tr\b.*?</tr>", html, re.I | re.S):
            cells = [strip_tags(td) for td in
                     re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, re.I | re.S)]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue
            if any(h in cells[0].lower() for h in ("name", "institution", "#", "no.")):
                continue  # header row
            link = re.search(r'href=["\'](https?://[^"\']+)["\']', tr, re.I)
            site = link.group(1) if link else ""
            if "sec.gov.gh" in site:
                site = ""
            rows.append([category, cells[0], " | ".join(cells[1:6]), site])
            found += 1
        print(f"  parsed {found} rows")

    if not rows:
        print("\nNo rows parsed. The page structure may not be a plain table —")
        print("open one of the URLs in a browser and tell me what you see.")
        return 1

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "name", "details_raw", "website"])
        w.writerows(rows)
    print(f"\nWrote {out_path} — {len(rows)} licensees across {len(SEC_PAGES)} pages")
    print("Pick your ten fund managers from this, then rerun without --sec.")
    return 0


def load_from_sec(path: str, category: str, limit: int) -> list[tuple[str, str]]:
    """Real providers and real URLs from the register, not from memory."""
    out: list[tuple[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if category and row.get("category", "").lower() != category.lower():
                continue
            site = (row.get("website") or "").strip()
            if not site:
                continue
            out.append((row["name"], site))
    return out[:limit] if limit else out


def run_discovery(targets: list[tuple[str, str]], out_path: str,
                  skip_wayback: bool = False) -> int:
    """
    Writes incrementally, so a run over 80+ sites can be interrupted without
    losing what it already found.
    """
    fields = ["provider", "site", "status", "best_price_url", "has_prices",
              "has_yield", "dates_on_page", "pdf_links", "wb_snapshots",
              "wb_distinct", "wb_first", "wb_last", "wb_note", "error",
              "MANUAL_cadence", "MANUAL_history_available", "MANUAL_fee_disclosed",
              "MANUAL_minimum_disclosed", "MANUAL_format", "MANUAL_verdict"]

    reachable = priced = dated = 0
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for i, (name, site) in enumerate(targets, 1):
            print(f"\n[{i}/{len(targets)}] {name}", flush=True)
            try:
                r = investigate(name, site, skip_wayback=skip_wayback)
            except KeyboardInterrupt:
                print("\nInterrupted — partial results saved.")
                break
            except Exception as e:                            # noqa: BLE001
                print(f"  crashed: {type(e).__name__}: {e}")
                continue

            if r.error:
                print(f"  UNREACHABLE: {r.error}")
            else:
                reachable += 1
                print(f"  candidates: {len(r.candidates)} (PDFs {r.pdf_count})", end="")
                if r.best_url:
                    priced += 1
                    print(f"  PRICE-LIKE: {r.best_url}")
                    if r.dates_found:
                        dated += 1
                        print(f"    dates: {r.dates_found}")
                    else:
                        print("    dates: NONE — unusable without a date")
                else:
                    print("  no price page found automatically")
            wb = r.wayback or {}
            if wb.get("snapshots"):
                print(f"    wayback: {wb['snapshots']} snaps / {wb['distinct']} versions "
                      f"{wb.get('note','')}")

            w.writerow([r.provider, r.site, r.site_status, r.best_url, r.has_prices,
                        r.has_yield, r.dates_found, r.pdf_count,
                        wb.get("snapshots", 0), wb.get("distinct", 0),
                        wb.get("first", ""), wb.get("last", ""), wb.get("note", ""),
                        r.error, "", "", "", "", "", ""])
            f.flush()

    n = len(targets)
    print(f"\n{'='*58}")
    print(f"  sites attempted            {n}")
    print(f"  reachable                  {reachable}")
    print(f"  price-like page found      {priced}")
    print(f"  ...and carrying a date     {dated}")
    print(f"{'='*58}")
    print("The last number is the one that matters. A price without a date")
    print("cannot be used, and a provider with no public price cannot be")
    print("scored from public data at all.")
    print(f"\nWrote {out_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="discovery.csv")
    ap.add_argument("--only", default="", help="substring filter on provider name")
    ap.add_argument("--sec", action="store_true",
                    help="scrape the SEC licensee register to sec_licensees.csv")
    ap.add_argument("--url", default="",
                    help="investigate a single site, e.g. --url https://example.com.gh")
    ap.add_argument("--from-sec", default="",
                    help="run discovery over sec_licensees.csv, e.g. --from-sec sec_licensees.csv")
    ap.add_argument("--category", default="Fund Managers")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--skip-wayback", action="store_true",
                    help="much faster; skips the cadence check")
    args = ap.parse_args()

    if args.sec:
        return scrape_sec("sec_licensees.csv")

    if args.url:
        r = investigate(args.url, args.url)
        print(json.dumps(asdict(r), indent=2, default=str))
        return 0

    if args.from_sec:
        targets = load_from_sec(args.from_sec, args.category, args.limit)
        if not targets:
            print(f"No rows with a website in {args.from_sec} for {args.category!r}")
            return 1
        print(f"Discovering across {len(targets)} {args.category} from the register")
        return run_discovery(targets, args.out, skip_wayback=args.skip_wayback)

    results: list[ProviderResult] = []
    targets = [(n, s) for n, s in PROVIDERS if args.only.lower() in n.lower()]

    for name, site in targets:
        print(f"\n=== {name} ===", flush=True)
        r = investigate(name, site)
        results.append(r)
        if r.error:
            print(f"  UNREACHABLE: {r.error}")
            continue
        print(f"  candidate pages : {len(r.candidates)}  (PDFs: {r.pdf_count})")
        if r.best_url:
            print(f"  price-like page : {r.best_url}")
            print(f"  prices={r.has_prices}  yields={r.has_yield}")
            print(f"  dates on page   : {r.dates_found or 'NONE FOUND — no date is a red flag'}")
        else:
            print("  price-like page : none found automatically — check by hand")
        w = r.wayback
        print(f"  wayback         : {w.get('snapshots', 0)} snapshots, "
              f"{w.get('distinct', 0)} distinct versions "
              f"({w.get('first', '?')} to {w.get('last', '?')}) {w.get('note', '')}")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["provider", "site", "status", "best_price_url", "has_prices",
                    "has_yield", "dates_on_page", "pdf_links", "wb_snapshots",
                    "wb_distinct", "wb_first", "wb_last", "wb_note",
                    "MANUAL_cadence", "MANUAL_history_available",
                    "MANUAL_fee_disclosed", "MANUAL_minimum_disclosed",
                    "MANUAL_format", "MANUAL_verdict"])
        for r in results:
            wb = r.wayback
            w.writerow([r.provider, r.site, r.site_status, r.best_url, r.has_prices,
                        r.has_yield, r.dates_found, r.pdf_count,
                        wb.get("snapshots", 0), wb.get("distinct", 0),
                        wb.get("first", ""), wb.get("last", ""), wb.get("note", ""),
                        "", "", "", "", "", ""])

    print(f"\nWrote {args.out}")
    print("The MANUAL_* columns are yours. The script narrows where to look;")
    print("it cannot judge whether a number is a fund NAV or a worked example.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

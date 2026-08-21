"""
faam_client.py — adapter for First Atlantic Asset Management factsheets.

THE THIRD ADAPTER, AND THE THIRD DIFFERENT SHAPE
  Stanbic  : predictable URL pattern -> enumerate months backwards
  ARG       : open REST catalogue, documents behind a paywall
  FAAM      : plain HTML listing, links exposed, WordPress Download Manager

That is the finding, not an inconvenience: there is no general Ghanaian fund
scraper. Each provider is its own adapter, roughly a few hours each, and the
fetching never generalises even when the extraction partly does.

TWO FUNDS, both listed at https://faam.com.gh/fund-fact-sheets/
  PIPS - First Atlantic Personal Investment Plan
  FAIF - First Atlantic Income Fund
17 monthly factsheets each, August 2024 to February 2026.

THE TRAP: the displayed title and the URL slug CONTRADICT each other.
    "DECEMBER 2025 PIPS FACT SHEET"  ->  december-2025-faif-fact-sheet-2
    "APRIL 2025 FAIF FACT SHEET"     ->  march-2025-faif-fact-sheet-2
One says PIPS, the other FAIF. One says April, the other March. So NEITHER is
authoritative. This records both, flags every disagreement, and leaves the
final say to the date and fund name printed inside the PDF — the same
conclusion the Stanbic files forced, where filename and content disagreed too.

Usage:
    python faam_client.py --list              # parse the listing, write a CSV
    python faam_client.py --download          # fetch every factsheet
    python faam_client.py --probe             # test two URLs and report shape
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

BASE = "https://faam.com.gh"
LISTING = BASE + "/fund-fact-sheets/"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/pdf,"
               "application/xml;q=0.9,*/*;q=0.8"),
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": LISTING,
}

MONTHS = {m.lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}
ABBR = {name[:3]: num for name, num in MONTHS.items()}

FUNDS = {
    "pips": "First Atlantic Personal Investment Plan",
    "faif": "First Atlantic Income Fund",
}


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 45) -> tuple[int, bytes, str]:
    """Returns (status, body, final_url). Follows redirects."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=_ctx()))
        with opener.open(req, timeout=timeout) as r:
            return getattr(r, "status", 200), r.read(), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, b"", url
    except Exception as e:                                   # noqa: BLE001
        print(f"    {type(e).__name__}: {e}")
        return 0, b"", url


def is_pdf(blob: bytes) -> bool:
    return blob[:5] == b"%PDF-"


def period_from(text: str) -> str:
    """YYYY-MM from 'FEBRUARY 2026 PIPS FACT SHEET' or 'nov-2024-pips'."""
    t = text.lower().replace("_", "-")
    m = re.search(r"([a-z]{3,9})[\s\-]+(\d{4})", t)
    if m:
        mon = MONTHS.get(m.group(1)) or ABBR.get(m.group(1)[:3])
        if mon:
            return f"{m.group(2)}-{mon:02d}"
    m = re.search(r"(\d{4})[\s\-]+([a-z]{3,9})", t)
    if m:
        mon = MONTHS.get(m.group(2)) or ABBR.get(m.group(2)[:3])
        if mon:
            return f"{m.group(1)}-{mon:02d}"
    return ""


def fund_from(text: str) -> str:
    t = text.lower()
    if "pips" in t:
        return "pips"
    if "faif" in t:
        return "faif"
    return ""


def parse_listing(html: str) -> list[dict]:
    """
    Pull every WordPress Download Manager link, with the title text that
    precedes it in the same table row.
    """
    rows: list[dict] = []
    seen: set[str] = set()

    for m in re.finditer(r"<tr\b.*?</tr>", html, re.I | re.S):
        block = m.group(0)
        link = re.search(r'href=["\'](https?://[^"\']*?/download/([^/"\']+)/'
                         r'\?wpdmdl=(\d+)[^"\']*)["\']', block, re.I)
        if not link:
            continue
        url, slug, dl_id = link.group(1), link.group(2), link.group(3)
        if dl_id in seen:
            continue
        seen.add(dl_id)
        text = re.sub(r"<[^>]+>", " ", block)
        text = re.sub(r"\s+", " ", text).strip()
        title = re.sub(r"\s*\d+(\.\d+)?\s*KB.*$", "", text, flags=re.I).strip()
        rows.append({"wpdmdl": dl_id, "slug": slug, "title": title, "url": url})

    if not rows:      # fall back to a flat anchor scan if the markup changed
        for m in re.finditer(r'href=["\'](https?://[^"\']*?/download/([^/"\']+)/'
                             r'\?wpdmdl=(\d+)[^"\']*)["\']', html, re.I):
            if m.group(3) in seen:
                continue
            seen.add(m.group(3))
            rows.append({"wpdmdl": m.group(3), "slug": m.group(2),
                         "title": "", "url": m.group(1)})
    return rows


def enrich(rows: list[dict]) -> list[dict]:
    """Derive fund and period from BOTH title and slug, and flag disagreement."""
    for r in rows:
        r["fund_title"] = fund_from(r["title"])
        r["fund_slug"] = fund_from(r["slug"])
        r["period_title"] = period_from(r["title"])
        r["period_slug"] = period_from(r["slug"])

        conflicts = []
        if r["fund_title"] and r["fund_slug"] and r["fund_title"] != r["fund_slug"]:
            conflicts.append(f"fund: title={r['fund_title']} slug={r['fund_slug']}")
        if (r["period_title"] and r["period_slug"]
                and r["period_title"] != r["period_slug"]):
            conflicts.append(f"period: title={r['period_title']} "
                             f"slug={r['period_slug']}")
        r["conflict"] = "; ".join(conflicts)
        # Prefer the title for display, but nothing here is authoritative —
        # the PDF's own "as at" line and fund name settle it.
        r["fund"] = r["fund_title"] or r["fund_slug"] or "unknown"
        r["period"] = r["period_title"] or r["period_slug"] or "undated"
        r["authoritative"] = "no - verify against PDF contents"
    return rows


def cmd_list(out_csv: str) -> int:
    print(f"Fetching {LISTING}\n")
    status, body, _ = fetch(LISTING)
    if status != 200 or not body:
        print(f"  failed: status {status}")
        return 1
    html = body.decode("utf-8", errors="replace")
    rows = enrich(parse_listing(html))
    if not rows:
        print("  No download links found — the page structure has changed.")
        print("  Open it in a browser, view source, and check the anchor format.")
        return 1

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "wpdmdl", "fund", "period", "title", "slug", "fund_title",
            "fund_slug", "period_title", "period_slug", "conflict",
            "authoritative", "url"])
        w.writeheader()
        w.writerows(rows)

    by_fund: dict[str, int] = {}
    for r in rows:
        by_fund[r["fund"]] = by_fund.get(r["fund"], 0) + 1
    print(f"  {len(rows)} factsheet link(s)")
    for fund, n in sorted(by_fund.items()):
        label = FUNDS.get(fund, fund)
        flag = "   <- clears MIN_HISTORY_MONTHS" if n >= 12 else ""
        print(f"    {n:>3}  {fund:<8} {label}{flag}")

    conflicts = [r for r in rows if r["conflict"]]
    if conflicts:
        print(f"\n  {len(conflicts)} row(s) where the title and slug DISAGREE:")
        for r in conflicts:
            print(f"    {r['title'][:44]:<46} slug={r['slug'][:40]}")
            print(f"       {r['conflict']}")
        print("  Neither source is authoritative. The PDF decides.")
    print(f"\n  wrote {out_csv}")
    return 0


def cmd_probe(list_csv: str) -> int:
    """Test two downloads and report exactly what comes back."""
    if not os.path.exists(list_csv):
        print(f"{list_csv} not found — run --list first")
        return 1
    rows = list(csv.DictReader(open(list_csv, encoding="utf-8")))[:2]
    for r in rows:
        print(f"\n{r['title'][:60]}")
        print(f"  {r['url']}")
        status, body, final = fetch(r["url"])
        print(f"  status {status}, {len(body):,} bytes")
        if final != r["url"]:
            print(f"  redirected to: {final}")
        if is_pdf(body):
            print("  -> real PDF")
        elif body[:15].lower().startswith(b"<!doctype") or b"<html" in body[:400].lower():
            print("  -> HTML, not a PDF (a landing page, or a gate)")
        else:
            print(f"  -> unknown, starts {body[:16]!r}")
        time.sleep(1.5)
    return 0


def cmd_download(list_csv: str, out_dir: str, delay: float) -> int:
    if not os.path.exists(list_csv):
        print(f"{list_csv} not found — run --list first")
        return 1
    rows = list(csv.DictReader(open(list_csv, encoding="utf-8")))
    ok = fail = skip = 0
    for r in rows:
        folder = os.path.join(out_dir, f"faam_{r['fund']}")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"faam_{r['fund']}_{r['period']}.pdf")
        if os.path.exists(path):
            skip += 1
            continue
        status, body, _ = fetch(r["url"])
        if status == 200 and is_pdf(body):
            with open(path, "wb") as f:
                f.write(body)
            ok += 1
            print(f"  OK    {r['fund']:<6} {r['period']:<9} {len(body):>8,} bytes")
        else:
            fail += 1
            print(f"  FAIL  {r['fund']:<6} {r['period']:<9} status {status}")
        time.sleep(delay)
    print(f"\n  {ok} downloaded, {skip} already present, {fail} failed -> {out_dir}")
    if ok:
        print(f"  Next: python extract_navs.py --dir {out_dir} --compute")
        print("  Expect blank fields — FAAM's layout will not match Stanbic's.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--csv", default="faam_factsheets.csv")
    ap.add_argument("--out", default="data/faam")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    if args.list:
        return cmd_list(args.csv)
    if args.probe:
        return cmd_probe(args.csv)
    if args.download:
        return cmd_download(args.csv, args.out, args.delay)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

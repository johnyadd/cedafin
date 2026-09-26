"""
discover_documents.py - the documents, not just the pages.

WHY THIS EXISTS, AND WHAT IT CORRECTS
Every discovery scan on this project used to read WEB PAGES only. A PDF behind
a download link was fetched as bytes, decoded as nonsense, and matched against
nothing. So "we checked their websites and found nothing" meant "we read the
pages, not the documents". This tool follows each provider's own navigation,
downloads the documents it finds, and reads them.

WHAT CHANGED IN v2 (September 2026)
  1. A PER-PROVIDER OUTCOME FILE. v1 printed "UNREACHABLE" to the screen and
     saved nothing per provider, so "read and found nothing", "refused us" and
     "JavaScript site" were indistinguishable afterwards. v2 writes one row per
     provider with an outcome the disclosure pages can state honestly:
        published     - a document was read and a relevant figure matched
        not_found     - pages/documents were read and nothing matched
        refused       - the site answered but refused us (401/403/406/429/503)
        unreachable   - no answer at all (DNS, timeout, TLS, connection reset)
        js_suspected  - the home page carries scripts but almost no links: its
                        navigation is built by JavaScript, which this cannot run
  2. DOCUMENTS RANKED BEFORE THE CAP. v1 kept the first --max-docs documents in
     the order found, so eight annual reports could push a tariff guide out.
     v2 ranks tariff/pricing/fee documents first and annual reports last, and
     records when the cap was reached ("capped"), instead of dropping silently.
  3. DATED OUTPUT. Files go to reports/scans/<YYYY-MM>/<type>_documents.csv and
     <type>_outcomes.csv, not loose in the repo root.
  4. SETTINGS FROM cedafin_env.py, like the scheduled scripts.

WHAT IT STILL CANNOT SEE, AND THE RECORD SHOULD SAY SO
  - Text inside an image (no OCR). A document with no text layer is recorded
    as "held, not read" and counted in docs_no_text.
  - Links that only appear after JavaScript runs.
  - Anything behind a login, on social media, in a newspaper, or on a wall.
  So not_found means "this scan did not find it, on this date, in the places it
  can reach" - never "publishes nothing".

HOW IT IDENTIFIES ITSELF
Honestly by default (CedafinBot, as the methodology page describes). --browser
sends a browser-shaped header for cases where a person would read the page
anyway; the outcome file records which identity was used.

Usage (repo root):
    python discover_documents.py --type bank --limit 3
    python discover_documents.py --type broker
    python discover_documents.py --type bank --browser --max-docs 20
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

from cedafin_env import supabase_config

HONEST_UA = (
    "Mozilla/5.0 (compatible; CedafinBot/1.0; "
    "+https://www.cedafin.com/methodology; data@cedafin.com)"
)
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

DOC_RX = re.compile(r"\.(pdf|docx?|xlsx?)(\?|$)", re.I)

# Where a document about prices is likely to be linked from.
FOLLOW_RX = re.compile(
    r"tariff|fee|charge|pricing|rate|download|document|form|guide|"
    r"account|loan|mortgage|savings|deposit|invest|brokerage|commission",
    re.I,
)
SKIP_RX = re.compile(
    r"login|signin|register|careers|news|media|press|blog|privacy|cookie|"
    r"terms|sitemap|contact|branch|swift|tender|vacanc|facebook|twitter|"
    r"linkedin|instagram|youtube",
    re.I,
)

# Document priority before the cap: lower number = kept first.
DOC_PRIORITY = [
    (0, re.compile(r"tariff|pricing|price[-_ ]?guide|charges|fees|schedule[-_ ]?of", re.I)),
    (1, re.compile(r"rate|interest|loan|mortgage|home[-_ ]?loan|savings|deposit|card|commission|brokerage", re.I)),
    (3, re.compile(r"annual[-_ ]?report|financial[-_ ]?statement|\bAR\b|agm|proxy|shareholder|notice", re.I)),
    (2, re.compile(r"form|application|opening|mandate|kyc", re.I)),
]

REFUSED_CODES = {401, 403, 406, 429, 503}

# What we are looking for once a document is open. Each pairs a subject with a
# figure: a bare keyword matches headings and menus.
NEAR = r"[^.\n]{0,70}"
AMOUNT = r"(?:GH[\u00a2C\u20b5]|GHS|USD|\$)\s?[\d,]+(?:\.\d{1,2})?"
PCT = r"\d{1,2}(?:\.\d{1,2})?\s*%"

PATTERNS = [
    (
        "rate",
        re.compile(
            rf"\b(interest|savings|deposit|lending|base|reference)\w*\b{NEAR}({PCT})"
            rf"|({PCT})\s*(?:p\.?a\.?|per\s+annum|a\s+year)",
            re.I,
        ),
    ),
    (
        "mortgage",
        re.compile(rf"\b(?:mortgage|home\s+loan)\b{NEAR}({PCT}|{AMOUNT})", re.I),
    ),
    (
        "commission",
        re.compile(rf"\b(commission|brokerage|dealing\s+fee)\b{NEAR}({PCT}|{AMOUNT})", re.I),
    ),
    (
        "fee",
        re.compile(
            rf"\b(monthly|maintenance|ledger|transfer|withdrawal|cheque|card|"
            rf"management|custody|processing|arrangement)\b{NEAR}({PCT}|{AMOUNT})",
            re.I,
        ),
    ),
]
PATTERN_LABELS = [label for label, _ in PATTERNS]


def doc_priority(url: str) -> int:
    name = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    for prio, rx in DOC_PRIORITY:
        if rx.search(name):
            return prio
    return 2


def providers(base: str, key: str, kind: str) -> list[dict]:
    req = urllib.request.Request(
        f"{base}/providers?select=slug,trading_name,website&provider_type=eq.{kind}"
        "&website=not.is.null&order=trading_name"
    )
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get(url: str, ua: str, binary: bool = False):
    """Returns (status, body, error). status 0 means no HTTP answer at all."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "*/*" if binary else "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read(30_000_000)
            return r.status, (data if binary else data.decode("utf-8", "replace")), ""
    except urllib.error.HTTPError as e:
        return e.code, None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return 0, None, f"{type(e).__name__}: {str(e)[:80]}"


def pdf_text(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        with open(path, "rb") as fh:
            reader = PdfReader(fh)
            return "\n".join((p.extract_text() or "") for p in reader.pages[:40])
    except Exception:  # noqa: BLE001
        return ""


def links_on(html: str, base: str) -> list[str]:
    out = []
    for href in re.findall(r'href="([^"#]+)"', html):
        u = urllib.parse.urljoin(base, href)
        if urllib.parse.urlparse(u).netloc != urllib.parse.urlparse(base).netloc:
            continue
        if SKIP_RX.search(u):
            continue
        out.append(u.split("?")[0] if not DOC_RX.search(u) else u)
    return list(dict.fromkeys(out))


def looks_js_built(html: str, n_links: int) -> bool:
    """Scripts present but almost no same-site links: the menu is built by JavaScript."""
    return n_links <= 3 and html.lower().count("<script") >= 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", default="bank", help="bank | broker | fund_manager | savings_loans")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--max-docs", type=int, default=12)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--browser", action="store_true", help="browser-shaped request")
    ap.add_argument("--out-dir", default=os.path.join("reports", "scans", date.today().strftime("%Y-%m")))
    args = ap.parse_args()

    base, key = supabase_config()
    ua = BROWSER_UA if args.browser else HONEST_UA
    identity = "browser" if args.browser else "cedafinbot"
    os.makedirs(args.out_dir, exist_ok=True)
    docs_csv = os.path.join(args.out_dir, f"{args.type}_documents.csv")
    outcomes_csv = os.path.join(args.out_dir, f"{args.type}_outcomes.csv")
    scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print()
    print(f"  Identifying as: {'a browser' if args.browser else 'CedafinBot (honest)'}")
    print(f"  Documents kept per provider: {args.max_docs}, tariff/pricing documents first.")
    print()

    rows: list[dict] = []
    outcomes: list[dict] = []
    provs = providers(base, key, args.type)
    if args.limit:
        provs = provs[: args.limit]

    for p in provs:
        name, slug, site = p["trading_name"], p["slug"], p["website"]
        host = urllib.parse.urlparse(site if "://" in site else f"https://{site}").netloc
        rec = {
            "provider": name, "slug": slug, "website": site, "host": host,
            "identity": identity, "scanned_at": scanned_at,
            "home_status": "", "outcome": "", "reason": "",
            "pages_read": 0, "docs_found": 0, "docs_kept": 0, "capped": False,
            "docs_downloaded": 0, "docs_failed": 0, "docs_no_text": 0,
            **{f"hits_{label}": 0 for label in PATTERN_LABELS},
        }
        if not host:
            rec.update(outcome="unreachable", reason="no usable website address")
            outcomes.append(rec)
            continue

        st, home, err = get(f"https://{host}/", ua)
        time.sleep(args.delay)
        rec["home_status"] = st
        if st != 200 or not home:
            rec["outcome"] = "refused" if st in REFUSED_CODES else "unreachable"
            rec["reason"] = err or f"HTTP {st}"
            print(f"  {name[:30]:<32} {rec['outcome'].upper()} ({rec['reason']})")
            outcomes.append(rec)
            continue

        home_links = links_on(home, f"https://{host}/")
        if looks_js_built(home, len(home_links)):
            rec["outcome"] = "js_suspected"
            rec["reason"] = f"{len(home_links)} same-site links, {home.lower().count('<script')} scripts on the home page"

        seen_pages = {f"https://{host}/"}
        queue = [u for u in home_links if FOLLOW_RX.search(u)]
        docs: list[str] = [u for u in home_links if DOC_RX.search(u)]
        pages = 0

        # Keep crawling past the cap's worth of documents: ranking happens after,
        # so a tariff guide found late can still displace an annual report.
        doc_budget = args.max_docs * 3
        while queue and pages < args.max_pages and len(docs) < doc_budget:
            u = queue.pop(0)
            if u in seen_pages or DOC_RX.search(u):
                continue
            seen_pages.add(u)
            st, html, _ = get(u, ua)
            time.sleep(args.delay)
            pages += 1
            if st != 200 or not html:
                continue
            for l in links_on(html, u):
                if DOC_RX.search(l):
                    if l not in docs:
                        docs.append(l)
                elif l not in seen_pages and FOLLOW_RX.search(l) and len(queue) < 60:
                    queue.append(l)

        rec["pages_read"] = pages
        rec["docs_found"] = len(docs)
        ranked = sorted(docs, key=lambda d: (doc_priority(d), docs.index(d)))
        kept = ranked[: args.max_docs]
        rec["docs_kept"] = len(kept)
        rec["capped"] = len(docs) > args.max_docs

        folder = os.path.join("data", "provider-docs", slug)
        os.makedirs(folder, exist_ok=True)
        found = {label: 0 for label in PATTERN_LABELS}

        for d in kept:
            fn = os.path.basename(urllib.parse.urlparse(d).path) or "document.pdf"
            path = os.path.join(folder, re.sub(r"[^A-Za-z0-9._-]", "_", fn))
            if not os.path.exists(path):
                st, raw, _ = get(d, ua, binary=True)
                time.sleep(args.delay)
                if st != 200 or not raw:
                    rec["docs_failed"] += 1
                    continue
                with open(path, "wb") as fh:
                    fh.write(raw)
            rec["docs_downloaded"] += 1
            text = pdf_text(path) if path.lower().endswith(".pdf") else ""
            if not text:
                rec["docs_no_text"] += 1
                rows.append({"provider": name, "slug": slug, "document": d,
                             "file": path, "pattern": "held, not read",
                             "snippet": "not a PDF, or no text layer"})
                continue
            for label, rx in PATTERNS:
                for m in list(rx.finditer(text))[:3]:
                    s = re.sub(r"\s+", " ", m.group(0))[:160]
                    rows.append({"provider": name, "slug": slug, "document": d,
                                 "file": path, "pattern": label, "snippet": s})
                    found[label] += 1

        for label in PATTERN_LABELS:
            rec[f"hits_{label}"] = found[label]
        if not rec["outcome"]:
            rec["outcome"] = "published" if any(found.values()) else "not_found"
        elif rec["outcome"] == "js_suspected" and any(found.values()):
            rec["outcome"] = "published"   # found anyway despite the JavaScript menu

        summary = ", ".join(f"{k} {v}" for k, v in found.items() if v) or "nothing in text"
        cap = " CAPPED" if rec["capped"] else ""
        print(f"  {name[:30]:<32} {pages:>2}p  {len(kept):>2}/{len(docs):<2} docs{cap}  "
              f"{rec['outcome']}  {summary}")
        outcomes.append(rec)

    with open(docs_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["provider", "slug", "document", "file", "pattern", "snippet"])
        w.writeheader()
        w.writerows(rows)
    with open(outcomes_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(outcomes[0].keys()) if outcomes else ["provider"])
        w.writeheader()
        w.writerows(outcomes)

    tally: dict[str, int] = {}
    for o in outcomes:
        tally[o["outcome"]] = tally.get(o["outcome"], 0) + 1
    print()
    print(f"  {len(rows)} finding(s) -> {docs_csv}")
    print(f"  {len(outcomes)} provider outcome(s) -> {outcomes_csv}")
    print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(tally.items())))
    capped = [o["provider"] for o in outcomes if o["capped"]]
    if capped:
        print(f"  Capped at {args.max_docs} documents: {', '.join(capped)} - rerun with a higher --max-docs if needed.")
    print()
    print("  not_found, refused, unreachable and js_suspected are NOT 'publishes nothing'.")
    print("  Read every snippet before believing it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

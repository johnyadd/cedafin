"""
discover_documents.py — the documents, not just the pages.

WHY THIS EXISTS, AND WHAT IT CORRECTS
Every discovery scan on this project has read WEB PAGES. It follows a site's
links, takes the text, matches patterns. A PDF behind a download link is
fetched as bytes, decoded as nonsense, and matched against nothing.

So "we checked their websites and found nothing" has always meant "we read the
pages, not the documents". Absa's tariff guide page says, in its own words,
"select and download the relevant tariff pricing document" — the charges were
published all along, in a format no scan opened.

That puts several published findings in doubt, all resting on the same blind
spot: that only Republic publishes a mortgage rate, that no stockbroker
publishes a commission, that most banks publish no savings rate. Each was a
fact about the scanner as much as about the market. This tool exists to test
them before any of them is repeated.

WHAT IT DOES
  1. Follows each provider's own navigation, looking for documents.
  2. Downloads what it finds into data/provider-docs/<slug>/ — the archive.
  3. Reads the text and reports where a rate, a fee or a commission appears.

WHAT IT STILL CANNOT SEE, AND THE RECORD SHOULD SAY SO
  - Text inside an image. A scanned tariff board needs OCR, which this has not.
  - Links that only appear after JavaScript runs. Absa's own download list is
    one: the page carries the words, and a plain fetch sees no links.
  - Anything behind a login, on social media, in a newspaper, or on a wall in
    a branch. All are real publication; none is collectible here.
  So a provider with no hit is not proven to publish nothing. It means this
  scan did not find it, on this date, in the places it can reach.

HOW IT IDENTIFIES ITSELF
Honestly, by default — the user agent the methodology page describes. Large
Ghanaian bank sites often refuse it. Where that happens the provider is
reported as unreachable rather than as publishing nothing, which is the
honest outcome. --browser sends a browser-shaped header instead, for the
cases where a person would then read the page anyway; it prints which was
used so the record can say.

Usage:
    python discover_documents.py --type bank --limit 3
    python discover_documents.py --type broker
    python discover_documents.py --type bank --browser
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
        re.compile(rf"\bmortgage|home\s+loan\b{NEAR}({PCT}|{AMOUNT})", re.I),
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


def providers(kind: str) -> list[dict]:
    req = urllib.request.Request(
        f"{BASE}/providers?select=slug,trading_name,website&provider_type=eq.{kind}"
        "&website=not.is.null&order=trading_name"
    )
    req.add_header("apikey", KEY)
    req.add_header("Authorization", f"Bearer {KEY}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get(url: str, ua: str, binary: bool = False):
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
            return r.status, data if binary else data.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def pdf_text(raw: bytes, path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        with open(path, "rb") as fh:
            reader = PdfReader(fh)
            return "\n".join((p.extract_text() or "") for p in reader.pages[:40])
    except Exception:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", default="bank", help="bank | broker | fund_manager | savings_loans")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--max-docs", type=int, default=12)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--browser", action="store_true", help="browser-shaped request")
    ap.add_argument("--out", default="provider_documents.csv")
    args = ap.parse_args()

    ua = BROWSER_UA if args.browser else HONEST_UA
    print()
    print(f"  Identifying as: {'a browser' if args.browser else 'CedafinBot (honest)'}")
    print("  Following each site's own navigation, and opening what it finds.")
    print()

    rows: list[dict] = []
    unreachable: list[str] = []
    provs = providers(args.type)
    if args.limit:
        provs = provs[: args.limit]

    for p in provs:
        name, slug, site = p["trading_name"], p["slug"], p["website"]
        host = urllib.parse.urlparse(site if "://" in site else f"https://{site}").netloc
        if not host:
            continue
        st, home = get(f"https://{host}/", ua)
        time.sleep(args.delay)
        if st != 200 or not home:
            print(f"  {name[:30]:<32} UNREACHABLE ({st})")
            unreachable.append(name)
            continue

        seen_pages = {f"https://{host}/"}
        queue = [u for u in links_on(home, f"https://{host}/") if FOLLOW_RX.search(u)]
        docs: list[str] = [u for u in queue if DOC_RX.search(u)]
        pages = 0

        while queue and pages < args.max_pages and len(docs) < args.max_docs:
            u = queue.pop(0)
            if u in seen_pages or DOC_RX.search(u):
                continue
            seen_pages.add(u)
            st, html = get(u, ua)
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

        docs = docs[: args.max_docs]
        folder = os.path.join("data", "provider-docs", slug)
        os.makedirs(folder, exist_ok=True)
        found: dict[str, int] = {}

        for d in docs:
            fn = os.path.basename(urllib.parse.urlparse(d).path) or "document.pdf"
            path = os.path.join(folder, re.sub(r"[^A-Za-z0-9._-]", "_", fn))
            if not os.path.exists(path):
                st, raw = get(d, ua, binary=True)
                time.sleep(args.delay)
                if st != 200 or not raw:
                    continue
                with open(path, "wb") as fh:
                    fh.write(raw)
            text = pdf_text(b"", path) if path.lower().endswith(".pdf") else ""
            if not text:
                rows.append({"provider": name, "slug": slug, "document": d,
                             "file": path, "pattern": "held, not read",
                             "snippet": "not a PDF, or no text layer"})
                continue
            for label, rx in PATTERNS:
                for m in list(rx.finditer(text))[:3]:
                    s = re.sub(r"\s+", " ", m.group(0))[:160]
                    rows.append({"provider": name, "slug": slug, "document": d,
                                 "file": path, "pattern": label, "snippet": s})
                    found[label] = found.get(label, 0) + 1

        summary = ", ".join(f"{k} {v}" for k, v in found.items()) or "nothing in text"
        print(f"  {name[:30]:<32} {pages:>2}p  {len(docs):>2} docs  {summary}")

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["provider", "slug", "document", "file", "pattern", "snippet"])
        w.writeheader()
        w.writerows(rows)

    print()
    print(f"  {len(rows)} finding(s) -> {args.out}; documents under data/provider-docs/")
    if unreachable:
        print(f"  {len(unreachable)} unreachable: {', '.join(unreachable)}")
        print("  Unreachable is not 'publishes nothing'. Open one in a browser before saying so.")
    print()
    print("  Read every snippet before believing it. And remember what this")
    print("  cannot see: images, JavaScript-loaded links, logins, social media,")
    print("  newspapers, and a tariff board in a branch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

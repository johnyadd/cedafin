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
        held_unread   - documents were fetched but could not be read: no text
                        layer (images) or they were web pages, not documents
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

WHAT CHANGED IN v3 (September 2026), after a full v2 run was checked by hand
and 8 of its 12 "not_found" banks turned out to publish tariff guides:
  1. SAME ORGANISATION, OTHER HOSTS. v2 dropped every link off the exact host,
     so www/non-www mismatches (UBA) and group file servers (av.sc.com for
     Standard Chartered) were invisible. v3 follows pages on the same
     registrable domain and accepts documents there or on known file hosts.
  2. held_unread. A "document" that is really a web page (a redirect), or a PDF
     with no text layer, is no longer counted as read-and-found-nothing.
  3. PAGE-LEVEL MATCHING. v2 needed a keyword within 70 characters of a figure,
     which fails on tables (labels in one column, figures in another). v3
     counts a page when a charge category and an amount appear on it.
  4. COOKIES AND REDIRECTS. Sites that bounce a visitor through a cookie-setting
     redirect (HTTP 307) now get a cookie jar; a redirect that still loops is
     recorded as refused (bot protection), not unreachable.
  5. --only <slug[,slug]> to rescan chosen providers.
  6. A failed name lookup is retried once before a provider is unreachable.

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
import http.cookiejar
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

REFUSED_CODES = {401, 403, 406, 429, 503, 307, 308}

# Hosts that serve documents for many organisations (a bank's own site links
# its PDFs there). Documents on these are accepted; pages are not followed.
FILE_HOSTS = ("svdcdn.com", "amazonaws.com", "cloudfront.net", "blob.core.windows.net", "googleusercontent.com")

SECOND_LEVEL = {"com", "co", "org", "gov", "edu", "net", "ac", "or"}

# Page-level categories: a page counts when one of these AND an amount appear on it.
CATEGORIES = {
    "mortgage": re.compile(r"mortgage|home\s+loan", re.I),
    "commission": re.compile(r"brokerage|commission\s+rate|trading\s+commission|dealing\s+fee", re.I),
    "fee": re.compile(r"tariff|service\s+(fee|charge)|maintenance\s+(fee|charge)|account\s+maintenance|commission\s+on\s+turnover|"
                      r"\bCOT\b|processing\s+fee|facility\s+fee|arrangement\s+fee|card\s+(issuance|fee)|"
                      r"credit\s+card|debit\s+card|swift|management\s+fee|custody\s+fee", re.I),
}
MONEY_RX = re.compile(r"(GH[\u00a2C\u20b5]|GHS|USD|US\$|\$)\s?\d|\d\s?%", re.I)
RATE_LINE_RX = re.compile(r"(interest|per\s+annum|p\.a\.|annual\s+percentage|\bAPR\b|reference\s+rate|\bGRR\b)[^\n]{0,80}\d{1,2}(\.\d{1,2})?\s*%|"
                          r"\d{1,2}(\.\d{1,2})?\s*%[^\n]{0,40}(per\s+annum|p\.a\.|a\s+year|per\s+month)", re.I)

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


def org_domain(host: str) -> str:
    """Registrable domain: www.ubaghana.com -> ubaghana.com; www.cbg.com.gh -> cbg.com.gh."""
    parts = host.lower().split(":")[0].split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def same_org(u: str, base: str) -> bool:
    return org_domain(urllib.parse.urlparse(u).netloc) == org_domain(urllib.parse.urlparse(base).netloc)


def on_file_host(u: str) -> bool:
    h = urllib.parse.urlparse(u).netloc.lower()
    return any(h == fh or h.endswith("." + fh) for fh in FILE_HOSTS)


def start_and_scope(site: str) -> tuple[str, str]:
    """Start at the stored address, path included (www.sc.com/gh -> https://www.sc.com/gh),
    and, for a country section of a group site, return that section ('gh') as the scope."""
    u = urllib.parse.urlparse(site if "://" in site else f"https://{site}")
    path = u.path.rstrip("/") or ""
    seg = path.strip("/").split("/")[0].lower() if path.strip("/") else ""
    return urllib.parse.urlunparse(("https", u.netloc, (path or "") + "/", "", "", "")), seg


def in_scope(u: str, seg: str) -> bool:
    """On a group site, stay inside the country section: pages under /<seg>/, documents with /<seg>/ in the path."""
    if not seg:
        return True
    return f"/{seg}/" in (urllib.parse.urlparse(u).path.lower().rstrip("/") + "/")


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


OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def get(url: str, ua: str, binary: bool = False, _retry: bool = True):
    """Returns (status, body, error). status 0 means no HTTP answer at all.
    Cookies are kept (some sites set one via a 307 before serving the page);
    a failed name lookup is retried once after a pause."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "*/*" if binary else "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        },
    )
    try:
        with OPENER.open(req, timeout=60) as r:
            data = r.read(30_000_000)
            return r.status, (data if binary else data.decode("utf-8", "replace")), ""
    except urllib.error.HTTPError as e:
        why = "redirect loop - likely bot protection" if e.code in (307, 308) else f"HTTP {e.code}"
        return e.code, None, why
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {str(e)[:80]}"
        if _retry and ("getaddrinfo" in msg or "Name or service not known" in msg or "timed out" in msg):
            time.sleep(3)
            return get(url, ua, binary, _retry=False)
        return 0, None, msg


def pdf_pages(path: str) -> list[str]:
    """Text of each page (first 40). Empty list if unreadable or no text layer."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    try:
        with open(path, "rb") as fh:
            head = fh.read(512)
        if head.lstrip()[:5].lower() in (b"<!doc", b"<html"):
            return []                      # a web page saved under a document name
        with open(path, "rb") as fh:
            reader = PdfReader(fh)
            pages = [(p.extract_text() or "") for p in reader.pages[:40]]
        return pages if any(t.strip() for t in pages) else []
    except Exception:  # noqa: BLE001
        return []


def is_html_file(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(512).lstrip()[:5].lower() in (b"<!doc", b"<html")
    except OSError:
        return False


def links_on(html: str, base: str) -> list[str]:
    out = []
    for href in re.findall(r'href=["\']([^"\'#]+)["\']', html):
        u = urllib.parse.urljoin(base, href)
        if not urllib.parse.urlparse(u).scheme.startswith("http"):
            continue
        if not same_org(u, base) and not (DOC_RX.search(u) and on_file_host(u)):
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
    ap.add_argument("--only", default="", help="comma-separated provider slugs to scan")
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
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        provs = [p for p in provs if p["slug"] in wanted]
        missing = wanted - {p["slug"] for p in provs}
        if missing:
            print(f"  Not found among --type {args.type} providers with a website: {', '.join(sorted(missing))}")
    if args.limit:
        provs = provs[: args.limit]

    for p in provs:
        name, slug, site = p["trading_name"], p["slug"], p["website"]
        host = urllib.parse.urlparse(site if "://" in site else f"https://{site}").netloc
        rec = {
            "provider": name, "slug": slug, "website": site, "host": host, "scope": "",
            "identity": identity, "scanned_at": scanned_at,
            "home_status": "", "outcome": "", "reason": "",
            "pages_read": 0, "docs_found": 0, "docs_kept": 0, "capped": False,
            "docs_downloaded": 0, "docs_failed": 0, "docs_no_text": 0, "docs_html": 0,
            **{f"hits_{label}": 0 for label in PATTERN_LABELS},
        }
        if not host:
            rec.update(outcome="unreachable", reason="no usable website address")
            outcomes.append(rec)
            continue

        start, scope = start_and_scope(site)
        st, home, err = get(start, ua)
        time.sleep(args.delay)
        if st == 0:                                   # no answer on https: try the stored http address
            st2, home2, err2 = get(start.replace("https://", "http://", 1), ua)
            time.sleep(args.delay)
            if st2:
                st, home, err, start = st2, home2, err2, start.replace("https://", "http://", 1)
        rec["home_status"] = st
        rec["scope"] = scope
        if st != 200 or not home:
            rec["outcome"] = "refused" if st in REFUSED_CODES else "unreachable"
            rec["reason"] = err or f"HTTP {st}"
            print(f"  {name[:30]:<32} {rec['outcome'].upper()} ({rec['reason']})")
            outcomes.append(rec)
            continue

        home_links = [l for l in links_on(home, start) if in_scope(l, scope)]
        if looks_js_built(home, len(home_links)):
            rec["outcome"] = "js_suspected"
            rec["reason"] = f"{len(home_links)} same-site links, {home.lower().count('<script')} scripts on the home page"

        seen_pages = {start}
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
                if not in_scope(l, scope):
                    continue
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
            if is_html_file(path):
                rec["docs_html"] += 1
                rows.append({"provider": name, "slug": slug, "document": d, "file": path,
                             "pattern": "held, not read", "snippet": "a web page, not a document (redirect?)"})
                continue
            pages_text = pdf_pages(path) if path.lower().endswith(".pdf") else []
            if not pages_text:
                rec["docs_no_text"] += 1
                rows.append({"provider": name, "slug": slug, "document": d, "file": path,
                             "pattern": "held, not read", "snippet": "not a PDF, or no text layer (image?)"})
                continue
            for pno, ptext in enumerate(pages_text, 1):
                if not MONEY_RX.search(ptext):
                    continue
                for label, rx in CATEGORIES.items():
                    m = rx.search(ptext)
                    if m:
                        line = next((l for l in ptext.splitlines() if MONEY_RX.search(l)), "")
                        rows.append({"provider": name, "slug": slug, "document": d, "file": path,
                                     "pattern": f"{label} (p{pno})",
                                     "snippet": re.sub(r"\s+", " ", f"{m.group(0)} ... {line}")[:160]})
                        found[label] += 1
                for m in list(RATE_LINE_RX.finditer(ptext))[:2]:
                    rows.append({"provider": name, "slug": slug, "document": d, "file": path,
                                 "pattern": f"rate (p{pno})", "snippet": re.sub(r"\s+", " ", m.group(0))[:160]})
                    found["rate"] += 1

        for label in PATTERN_LABELS:
            rec[f"hits_{label}"] = found[label]
        unread = rec["docs_no_text"] + rec["docs_html"]
        if any(found.values()):
            rec["outcome"] = "published"          # found, whatever the menu looked like
        elif not rec["outcome"]:
            if unread:
                rec["outcome"] = "held_unread"
                rec["reason"] = f"{rec['docs_no_text']} without a text layer, {rec['docs_html']} were web pages"
            elif not docs and home.lower().count("<script") >= 10:
                rec["outcome"] = "js_suspected"
                rec["reason"] = "pages read but no documents found; the site is script-heavy"
            else:
                rec["outcome"] = "not_found"

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
    print("  not_found, held_unread, refused, unreachable and js_suspected are NOT 'publishes nothing'.")
    print("  Read every snippet before believing it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

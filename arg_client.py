"""
arg_client.py — adapter for the annualreportsghana.com CIS repository.

WHY THIS IS THE MOST VALUABLE SOURCE FOUND SO FAR
It catalogues 72 Ghanaian collective investment schemes in one place — more of
the market than every individual provider website combined, and it reaches
funds whose own domains do not resolve at all (EDC) or whose sites have been
frozen since 2018 (Databank). It exposes an undocumented but open WordPress
REST API, so the whole catalogue is machine-readable.

WHAT IT IS AND IS NOT
  - Catalogue: EXCELLENT. 72 funds, with slugs preserving renames and
    acquisitions ("republic-unit-trust-formerly-hfc-unit-trust",
    "pinnacle-balanced-fund-previously-octanedc-bond-fund"). That identity
    history is the hardest part of building a fund catalogue and it is free.
  - Time series: THIN. 144 factsheets over 72 funds, but 115 of them belong to
    just five funds (Stanbic x2, EDC x3). Most funds have one or two documents.
So this fills the catalogue layer market-wide, and the series layer for five
funds. Everything else still needs the provider relationship.

TWO GOTCHAS, both found by inspecting real records:
  1. source_url is an INTERNAL s3:// path. The public URL is derived by
     swapping the prefix. guid.rendered usually holds the https URL but is
     sometimes malformed (a "prod-preview" host with a missing slash), so the
     derivation is the primary and guid is the fallback.
  2. Search is fuzzy — "EDC Money Market" returns OctaneDC funds because
     "DC Money Market" matches. Filter by fund id (the `post` field), never by
     search term, when you care which fund a document belongs to.

Usage:
    python arg_client.py --catalogue          # all 72 funds + doc index -> CSV
    python arg_client.py --download 983 968 950   # fetch docs for fund ids
    python arg_client.py --download-slug edc-ghana-money-market-unit-trust
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

BASE = "https://annualreportsghana.com"
API = BASE + "/wp-json/wp/v2"
S3_PREFIX = "s3://arg-reports-source/"
PUBLIC_PREFIX = BASE + "/wp-content/uploads/"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "application/json,application/pdf,*/*",
}


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def get(url: str, timeout: int = 45) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return getattr(r, "status", 200), r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, b"", {}
    except Exception as e:                                   # noqa: BLE001
        print(f"    error: {type(e).__name__}: {e}")
        return 0, b"", {}


def get_json(url: str) -> tuple[list, dict]:
    status, body, headers = get(url)
    if status != 200 or not body:
        return [], headers
    try:
        return json.loads(body), headers
    except json.JSONDecodeError:
        return [], headers


def paged(endpoint: str, fields: str, extra: str = "", per_page: int = 100) -> list:
    """Walk every page using X-WP-TotalPages rather than guessing."""
    out: list = []
    page = 1
    while True:
        url = (f"{API}/{endpoint}?per_page={per_page}&page={page}"
               f"&_fields={fields}{extra}")
        rows, headers = get_json(url)
        if not rows:
            break
        out += rows
        total_pages = int(headers.get("x-wp-totalpages")
                          or headers.get("X-WP-TotalPages") or 1)
        # The API reports totalpages relative to per_page=1 in some configs,
        # so stop on a short page as well.
        if page * per_page >= int(headers.get("x-wp-total") or 10**9):
            break
        page += 1
        time.sleep(0.6)
    return out


def public_url(rec: dict) -> str:
    """
    Derive the downloadable URL.

    source_url is internal (s3://arg-reports-source/...) and maps cleanly onto
    the public uploads path. guid.rendered is usually the https URL but has
    been seen malformed, so it is only the fallback.
    """
    src = rec.get("source_url") or ""
    if src.startswith(S3_PREFIX):
        return PUBLIC_PREFIX + src[len(S3_PREFIX):]
    guid = ((rec.get("guid") or {}).get("rendered") or "")
    if guid.startswith("http") and "prod-preview" not in guid:
        return guid
    if guid:
        # Repair the known malformation: missing slash after the host.
        fixed = re.sub(r"https?://[^/]*?annualreportsghana\.com(?=wp-content)",
                       BASE + "/", guid)
        if fixed.startswith("http"):
            return fixed
    return ""


def match_fund(rec: dict, url: str, by_id: dict, slugs: list[str]) -> str:
    """
    Resolve which fund a document belongs to.

    THE `post` FIELD IS NOT ENOUGH. Only 235 of 796 attachments carry a post
    that maps to a CIS fund, and those are almost entirely annual reports and
    logo images. The factsheets — the documents that matter — are attached to
    other post types or not attached at all, so joining on `post` alone found
    exactly ONE factsheet across the whole repository.

    The upload path is the reliable key: newer files live under
        /wp-content/uploads/cis/<fund-slug>/<year>/<month>/<file>.pdf
    Older ones (2019/07/, 2022/04/) predate that layout and fall back to
    matching the fund slug's distinctive words against the filename.
    """
    fund = by_id.get(rec.get("post"))
    if fund:
        return fund["slug"]

    m = re.search(r"/uploads/cis/([a-z0-9\-]+)/", url)
    if m and m.group(1) in slugs:
        return m.group(1)

    name = url.rsplit("/", 1)[-1].lower().replace("%20", "-")
    best = ""
    for slug in slugs:
        words = [w for w in slug.split("-")
                 if w not in ("fund", "trust", "the", "formerly", "previously",
                              "plc", "ltd", "limited", "unit", "scheme")]
        if len(words) >= 2 and all(w in name for w in words):
            if len(slug) > len(best):
                best = slug
    return best


def clean(s: str) -> str:
    """WordPress renders titles with HTML entities."""
    s = re.sub(r"<[^>]+>", "", s or "")
    for a, b in [("&#8211;", "-"), ("&#8217;", "'"), ("&amp;", "&"),
                 ("&#038;", "&"), ("&quot;", '"'), ("&#8220;", '"'),
                 ("&#8221;", '"')]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


DOC_KINDS = [
    ("factsheet", r"fact\s*sheet|factsheet"),
    ("annual_report", r"annual\s*report"),
    ("scheme_particulars", r"scheme\s*particulars"),
    ("prospectus", r"prospectus"),
    ("financials", r"financial\s*statement|half\s*year|interim"),
]


def classify(title: str, filename: str) -> str:
    hay = f"{title} {filename}".lower()
    for kind, pattern in DOC_KINDS:
        if re.search(pattern, hay):
            return kind
    return "other"


MONTHS = {m.lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}
# Lowercase keys — the lookup lowercases the month before matching, and an
# earlier version built capitalised keys here so every abbreviated month
# ("Jun 2025") silently fell through to the year-only branch.
ABBR = {name[:3]: num for name, num in MONTHS.items()}


def period_of(title: str, filename: str) -> str:
    """The period the DOCUMENT covers — not the date it was uploaded."""
    hay = f"{title} {filename}"
    m = re.search(r"([A-Z][a-z]{2,8})[\s\-_]+(\d{4})", hay)
    if m:
        name = m.group(1).lower()
        mon = MONTHS.get(name) or ABBR.get(name[:3])
        if mon:
            return f"{m.group(2)}-{mon:02d}"
    m = re.search(r"\b(20\d{2})\b", hay)
    return m.group(1) if m else ""


def build_catalogue(out_funds: str, out_docs: str) -> int:
    print("Fetching fund catalogue...")
    funds = paged("cis", "id,slug,title,link")
    print(f"  {len(funds)} funds")

    print("Fetching document index (all attachments, not a search)...")
    docs = paged("media", "id,date,slug,title,link,post,source_url,guid,mime_type")
    print(f"  {len(docs)} documents")

    by_id = {f["id"]: f for f in funds}
    slugs = [f["slug"] for f in funds]

    resolved: dict[int, str] = {}
    for d in docs:
        resolved[d["id"]] = match_fund(d, public_url(d), by_id, slugs)
    print(f"  {sum(1 for v in resolved.values() if v)} of {len(docs)} "
          f"resolved to a fund")

    with open(out_funds, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fund_id", "slug", "name", "former_name", "link", "doc_count",
                    "factsheets", "annual_reports"])
        counts: dict[str, list] = {}
        for d in docs:
            slug = resolved.get(d["id"])
            if slug:
                counts.setdefault(slug, []).append(d)
        for fund in sorted(funds, key=lambda x: x["slug"]):
            ds = counts.get(fund["slug"], [])
            name = clean((fund.get("title") or {}).get("rendered", ""))
            former = ""
            fm = re.search(r"(?:formerly|previously)[\s\-]+(.+)$", fund["slug"], re.I)
            if fm:
                former = fm.group(1).replace("-", " ")
            w.writerow([fund["id"], fund["slug"], name, former, fund.get("link", ""),
                        len(ds),
                        sum(1 for x in ds if classify(clean((x.get('title') or {}).get('rendered','')), x.get('slug','')) == "factsheet"),
                        sum(1 for x in ds if classify(clean((x.get('title') or {}).get('rendered','')), x.get('slug','')) == "annual_report")])

    with open(out_docs, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "fund_id", "fund_slug", "kind", "period", "title",
                    "download_url", "uploaded", "mime"])
        for d in sorted(docs, key=lambda x: (resolved.get(x["id"]) or "~",
                                            x.get("date") or "")):
            if (d.get("mime_type") or "").startswith("image/"):
                continue          # fund logos are attachments too
            title = clean((d.get("title") or {}).get("rendered", ""))
            url = public_url(d)
            fname = url.rsplit("/", 1)[-1] or d.get("slug", "")
            w.writerow([d["id"], d.get("post", ""), resolved.get(d["id"], ""),
                        classify(title, fname),
                        period_of(title, fname) or period_of(fname, ""),
                        title, url, (d.get("date") or "")[:10],
                        d.get("mime_type", "")])

    print(f"\nWrote {out_funds} and {out_docs}")
    print("\nFactsheets per fund — the series-layer number:")
    fs: dict[str, int] = {}
    for d in docs:
        slug = resolved.get(d["id"])
        if not slug or (d.get("mime_type") or "").startswith("image/"):
            continue
        url = public_url(d)
        title = clean((d.get("title") or {}).get("rendered", ""))
        if classify(title, url.rsplit("/", 1)[-1]) == "factsheet":
            fs[slug] = fs.get(slug, 0) + 1
    for slug, n in sorted(fs.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {n:>3}  {slug}{'   <- scoreable' if n >= 12 else ''}")
    print(f"\n  {len(fs)} fund(s) have a factsheet; "
          f"{sum(1 for n in fs.values() if n >= 12)} clear MIN_HISTORY_MONTHS")
    return 0


def download(fund_ids: list[int], slugs: list[str], docs_csv: str,
             out_dir: str, kinds: list[str], delay: float) -> int:
    if not os.path.exists(docs_csv):
        print(f"{docs_csv} not found — run --catalogue first")
        return 1
    rows = list(csv.DictReader(open(docs_csv, encoding="utf-8")))
    want = [r for r in rows
            if (str(r["fund_id"]) in {str(i) for i in fund_ids}
                or r["fund_slug"] in slugs)
            and (not kinds or r["kind"] in kinds)
            and r["download_url"]]
    if not want:
        print("Nothing matched. Check fund ids/slugs against arg_funds.csv")
        return 1

    print(f"Downloading {len(want)} document(s)\n")
    ok = fail = 0
    for r in want:
        folder = os.path.join(out_dir, r["fund_slug"])
        os.makedirs(folder, exist_ok=True)
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", r["title"])[:80] or f"doc{r['doc_id']}"
        period = r["period"] or "undated"
        path = os.path.join(folder, f"{period}__{stem}.pdf")
        if os.path.exists(path):
            print(f"  skip (have)  {r['fund_slug']}  {period}")
            continue
        status, body, _ = get(r["download_url"])
        if status == 200 and body[:5] == b"%PDF-":
            with open(path, "wb") as f:
                f.write(body)
            ok += 1
            print(f"  OK    {r['fund_slug']:<44} {period}  {len(body):>8,} bytes")
        else:
            fail += 1
            print(f"  FAIL  {r['fund_slug']:<44} {period}  status {status}")
            print(f"        {r['download_url']}")
        time.sleep(delay)

    print(f"\n  {ok} downloaded, {fail} failed -> {out_dir}")
    if ok:
        print("  Next: python extract_navs.py --dir " + out_dir + " --compute")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", action="store_true")
    ap.add_argument("--funds-csv", default="arg_funds.csv")
    ap.add_argument("--docs-csv", default="arg_docs.csv")
    ap.add_argument("--download", nargs="*", type=int, default=[],
                    help="fund ids, e.g. --download 983 968 950")
    ap.add_argument("--download-slug", nargs="*", default=[])
    ap.add_argument("--kinds", nargs="*", default=["factsheet"],
                    help="factsheet annual_report scheme_particulars prospectus; empty for all")
    ap.add_argument("--out", default="data/arg")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    if args.catalogue:
        return build_catalogue(args.funds_csv, args.docs_csv)
    if args.download or args.download_slug:
        return download(args.download, args.download_slug, args.docs_csv,
                        args.out, args.kinds, args.delay)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

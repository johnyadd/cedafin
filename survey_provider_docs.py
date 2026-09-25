"""
survey_provider_docs.py - which providers publish their charges in documents?

Read-only. Walks every folder under data/provider-docs/, and for every PDF:
  1. classifies it: tariff_guide, annual_report, form, rates_sheet, other
  2. (except annual reports and very long documents) finds pages mentioning
     charge categories: mortgage, credit card, personal loan, overdraft,
     account fees, debit card, transfers - and lines stating an interest rate
  3. records any date it states, and the PDF's own modified date

Writes to data/provider-docs/_inspection/survey_<YYYYMMDD_HHMM>/:
  summary.txt       - paste this first: per-provider rollup + one line per document
  summary.csv       - the same, as a table
  <provider>.txt    - pages with charges, laid out as tables, for providers with hits

Never modifies a PDF, never touches the database, never goes online.

Usage (repo root, venv active):
    python survey_provider_docs.py
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "data" / "provider-docs"

MAX_DEEP_PAGES = 60          # longer documents are classified but not scanned page by page
MAX_DUMP_PAGES_PER_DOC = 8   # pages laid out in a provider's detail file, per document

ALREADY_LOADED = {           # read in full and loaded on 23 Sept 2026
    "TARIFF-GUIDE_MARCH2026-PUBLIC-V2.pdf",
    "FNBGH_HomeLoans_Pricing_Guide.pdf",
    "tariff-guide.pdf",
    "tariff-guide-premier.pdf",
    "Individual-or-Joint-Account-Opening-002.pdf",
}

# --- classification -----------------------------------------------------------
NAME_TARIFF = re.compile(r"tariff|pricing|price[-_ ]?guide|charges|fees|schedule[-_ ]?of", re.I)
TEXT_TARIFF = re.compile(r"tariff|pricing guide|schedule of (fees|charges)|fees and charges|"
                         r"service charges|charges and fees", re.I)
NAME_ANNUAL = re.compile(r"annual|financial[-_ ]?statement|\bAR\b|[-_]FS[-_]", re.I)
TEXT_ANNUAL = re.compile(r"annual report|financial statements|report of the directors|"
                         r"independent auditor", re.I)
NAME_FORM = re.compile(r"form|application|opening|mandate|kyc", re.I)
TEXT_FORM = re.compile(r"application form|account opening|please (complete|tick)|signature of", re.I)
NAME_RATES = re.compile(r"rate", re.I)

# --- charge categories ------------------------------------------------------------
CATEGORIES = {
    "mortgage": re.compile(r"mortgage|home loan", re.I),
    "credit_card": re.compile(r"credit card|visa credit|mastercard credit", re.I),
    "personal_loan": re.compile(r"personal loan|consumer loan|salary loan|scheme loan", re.I),
    "overdraft": re.compile(r"overdraft", re.I),
    "account_fees": re.compile(r"monthly (service|maintenance) (fee|charge)|account maintenance|"
                               r"ledger fee|commission on turnover|\bCOT\b|monthly fee", re.I),
    "debit_card": re.compile(r"debit card", re.I),
    "transfers": re.compile(r"\bswift\b|telegraphic|outward transfer|inward remittance", re.I),
    # fund managers and brokers - the two standing "publishes nothing" findings
    "investment_fees": re.compile(r"management fee|fee of the investment manager|agreed fee|entry fee|"
                                  r"exit fee|front[- ]end (fee|load)|back[- ]end (fee|load)|"
                                  r"total expense ratio|\bTER\b", re.I),
    "brokerage_commission": re.compile(r"brokerage (fee|commission|charge)|commission rate|"
                                       r"trading commission|commission of \d", re.I),
}
MONEY = re.compile(r"(GHS|GH¢|GH₵|¢|USD|US\$|\$|GBP|£|EUR|€)\s?\d|\d\s?%", re.I)
INTEREST_LINE = re.compile(r"(interest rate|per annum|p\.a\.|per month|annual percentage|APR)", re.I)
PCT = re.compile(r"\d+(\.\d+)?\s?%")

MONTHS = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
DATE_TEXT = re.compile(rf"\b({MONTHS}\s+20[12]\d|\d{{1,2}}\s+{MONTHS}\s+20[12]\d|20[12]\d)\b", re.I)

WIDE_GAP = re.compile(r" {6,}")


def text_of(page, layout=False) -> str:
    try:
        if layout:
            return page.extract_text(extraction_mode="layout") or ""
        return page.extract_text() or ""
    except Exception:  # noqa: BLE001
        try:
            return page.extract_text() or ""
        except Exception:  # noqa: BLE001
            return ""


def tidy(text: str) -> str:
    out = []
    for line in text.splitlines():
        line = line.rstrip()
        if line.strip():
            out.append(WIDE_GAP.sub("  |  ", line))
    return "\n".join(out)


def pdf_modified(reader) -> str:
    try:
        md = reader.metadata or {}
        raw = str(md.get("/ModDate") or md.get("/CreationDate") or "")
        m = re.search(r"(\d{4})(\d{2})(\d{2})", raw)
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""
    except Exception:  # noqa: BLE001
        return ""


def classify(name: str, head: str, n_pages: int) -> str:
    if NAME_TARIFF.search(name) or TEXT_TARIFF.search(head):
        return "tariff_guide"
    if NAME_ANNUAL.search(name) or (TEXT_ANNUAL.search(head) and n_pages > 30):
        return "annual_report"
    if NAME_FORM.search(name) or TEXT_FORM.search(head):
        return "form"
    if NAME_RATES.search(name):
        return "rates_sheet"
    return "other"


def survey_pdf(path: Path) -> dict:
    rec = {
        "provider": path.parent.name, "file": path.name, "pages": 0, "kind": "",
        "stated_date": "", "pdf_modified": "", "categories": "", "interest_lines": 0,
        "money_lines": 0, "hit_pages": "", "loaded": "yes" if path.name in ALREADY_LOADED else "",
        "error": "", "_pages_by_cat": {}, "_reader": None,
    }
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:  # noqa: BLE001
                rec["error"] = "encrypted"
                return rec
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"unreadable: {type(e).__name__}"
        return rec

    try:
        return _survey_contents(reader, rec, path)
    except Exception as e:  # noqa: BLE001
        # One bad PDF (encryption, broken structure) is recorded and skipped, never fatal.
        rec["error"] = f"{type(e).__name__}: {str(e)[:80]}"
        rec["_pages_by_cat"], rec["_reader"] = {}, None
        return rec


def _survey_contents(reader, rec: dict, path: Path) -> dict:
    n = len(reader.pages)
    rec["pages"] = n
    rec["pdf_modified"] = pdf_modified(reader)
    head = "\n".join(text_of(reader.pages[i]) for i in range(min(3, n)))
    rec["kind"] = classify(path.name, head, n)
    m = DATE_TEXT.search(head)
    rec["stated_date"] = m.group(0) if m else ""

    if not head.strip():
        rec["error"] = "no extractable text in first pages (image-only?)"

    if rec["kind"] == "annual_report" or n > MAX_DEEP_PAGES:
        return rec

    pages_by_cat: dict[str, list[int]] = defaultdict(list)
    interest_lines = money_lines = 0
    for i in range(n):
        t = text_of(reader.pages[i])
        for line in t.splitlines():
            if MONEY.search(line):
                money_lines += 1
                if INTEREST_LINE.search(line) and PCT.search(line):
                    interest_lines += 1
        # a category counts on a page only if that page also carries amounts
        if MONEY.search(t):
            for cat, rx in CATEGORIES.items():
                if rx.search(t):
                    pages_by_cat[cat].append(i + 1)

    rec["interest_lines"] = interest_lines
    rec["money_lines"] = money_lines
    rec["categories"] = ";".join(sorted(pages_by_cat))
    rec["hit_pages"] = " ".join(f"{c}:{','.join(map(str, p))}" for c, p in sorted(pages_by_cat.items()))
    rec["_pages_by_cat"] = pages_by_cat
    rec["_reader"] = reader
    return rec


def main():
    if not DOCS.exists():
        sys.exit(f"Not found: {DOCS} - run from the repo root.")
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = DOCS / "_inspection" / f"survey_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    folders = sorted(p for p in DOCS.iterdir() if p.is_dir() and not p.name.startswith("_"))
    records = []
    for fi, folder in enumerate(folders, 1):
        pdfs = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".pdf")
        print(f"[{fi}/{len(folders)}] {folder.name} ({len(pdfs)} PDFs)")
        for pdf in pdfs:
            records.append(survey_pdf(pdf))

    # ---- per-provider detail files
    detail_written = []
    by_provider: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_provider[r["provider"]].append(r)
    for prov, recs in by_provider.items():
        lines = []
        for r in recs:
            if not r["_pages_by_cat"] or r["_reader"] is None:
                continue
            reader = r["_reader"]
            lines.append("=" * 100)
            lines.append(f"{r['file']}  [{r['kind']}, {r['pages']} pages, "
                         f"stated date: {r['stated_date'] or 'none'}, pdf modified: {r['pdf_modified'] or '?'}"
                         f"{', ALREADY LOADED' if r['loaded'] else ''}]")
            lines.append(f"charge pages: {r['hit_pages']}   interest-rate lines: {r['interest_lines']}")
            lines.append("=" * 100)
            wanted = sorted({p for ps in r["_pages_by_cat"].values() for p in ps})
            for p in wanted[:MAX_DUMP_PAGES_PER_DOC]:
                lines.append(f"\n--- page {p} of {r['pages']} ---")
                lines.append(tidy(text_of(reader.pages[p - 1], layout=True)))
            if len(wanted) > MAX_DUMP_PAGES_PER_DOC:
                lines.append(f"\n(showing {MAX_DUMP_PAGES_PER_DOC} of {len(wanted)} charge pages)")
            lines.append("")
        if lines:
            f = out_dir / f"{prov}.txt"
            f.write_text("\n".join(lines), encoding="utf-8")
            detail_written.append((prov, f.stat().st_size))

    # ---- summary.csv
    cols = ["provider", "file", "pages", "kind", "stated_date", "pdf_modified", "categories",
            "interest_lines", "money_lines", "hit_pages", "loaded", "error"]
    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)

    # ---- summary.txt
    s = [f"Provider document survey - {datetime.now():%Y-%m-%d %H:%M}",
         f"{len(records)} PDFs in {len(folders)} provider folders", ""]

    tariff_providers = sorted({r["provider"] for r in records if r["kind"] == "tariff_guide"})
    charge_providers = sorted({r["provider"] for r in records if r["categories"]})
    empty_folders = sorted(f.name for f in folders if not any(p.suffix.lower() == ".pdf" for p in f.iterdir()))
    s.append(f"Providers holding a document classified as a tariff/pricing guide: {len(tariff_providers)}")
    for p in tariff_providers:
        s.append(f"   {p}")
    s.append(f"Providers with any document showing charges (a category plus amounts on the same page): "
             f"{len(charge_providers)}")
    s.append(f"Folders with no PDF at all: {len(empty_folders)}"
             + (f" - {', '.join(empty_folders)}" if empty_folders else ""))
    s.append("")

    s.append("PER PROVIDER  (docs / tariff guides / docs with charges / categories found)")
    for prov in sorted(by_provider):
        recs = by_provider[prov]
        cats = sorted({c for r in recs for c in r["categories"].split(";") if c})
        s.append(f"  {prov:58} {len(recs):>3} / {sum(r['kind'] == 'tariff_guide' for r in recs):>2} / "
                 f"{sum(bool(r['categories']) for r in recs):>2}   {', '.join(cats)}")
    s.append("")

    s.append("DOCUMENTS WITH CHARGES OR CLASSIFIED AS TARIFF  (loaded / kind / pages / date / categories / rate lines)")
    for r in records:
        if r["kind"] == "tariff_guide" or r["categories"]:
            s.append(f"  {'*' if r['loaded'] else ' '} {r['provider'][:34]:34} {r['file'][:52]:52} "
                     f"{r['kind']:13} {r['pages']:>4}p  {(r['stated_date'] or '-')[:18]:18} "
                     f"{r['categories'] or '-'}  [{r['interest_lines']}]")
    s.append("  (* = already read in full and loaded)")
    s.append("")

    problems = [r for r in records if r["error"]]
    if problems:
        s.append("COULD NOT READ PROPERLY")
        for r in problems:
            s.append(f"  {r['provider'][:34]:34} {r['file'][:52]:52} {r['error']}")
        s.append("")

    s.append("DETAIL FILES (paste only the ones worth reading)")
    for prov, size in sorted(detail_written):
        s.append(f"  {prov}.txt  ({size / 1024:.0f} KB)")

    (out_dir / "summary.txt").write_text("\n".join(s), encoding="utf-8")
    print(f"\nSurvey written to: {out_dir}")
    print("Paste summary.txt first.")


if __name__ == "__main__":
    main()

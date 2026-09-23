"""
inspect_docs.py - run every pending provider-document check in one pass.

Reads the PDFs already archived under data/provider-docs/, writes one report:
    data/provider-docs/_inspection/report_<YYYYMMDD_HHMM>.txt

Read-only: it never modifies a PDF or touches the database.

Usage (from C:\\Projects\\cediwise, engine venv active):
    python inspect_docs.py

To add a check later, add an entry to JOBS at the bottom.
Job kinds:
    layout  - print given pages (1-based) with table columns kept in position
    match   - print, in layout, every page whose text matches a pattern
              (plus `neighbours` pages either side), up to `cap` pages
    grep    - print every line matching a pattern, with page number
    dates   - print every line mentioning 2019-2029 (to date the document)
    fields  - print the PDF's form fields and any values filled in
"""

import re
import sys
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "data" / "provider-docs"
OUT_DIR = DOCS / "_inspection"

WIDE_GAP = re.compile(r" {6,}")        # long runs of spaces from layout mode
DATE_LINE = re.compile(r"\b20(19|2[0-9])\b")


class Report:
    def __init__(self):
        self.lines = []

    def add(self, text=""):
        self.lines.append(text)

    def heading(self, text):
        self.add("")
        self.add("=" * 100)
        self.add(text)
        self.add("=" * 100)

    def sub(self, text):
        self.add("")
        self.add(f"--- {text} ---")


def open_pdf(rel_path, report):
    path = DOCS / rel_path
    if not path.exists():
        report.add(f"!! FILE NOT FOUND: {path}")
        return None
    try:
        return PdfReader(str(path))
    except Exception as e:  # noqa: BLE001
        report.add(f"!! COULD NOT OPEN {path.name}: {e}")
        return None


def page_text(page, layout=False):
    try:
        if layout:
            return page.extract_text(extraction_mode="layout") or ""
        return page.extract_text() or ""
    except Exception as e:  # noqa: BLE001
        # Older pypdf without layout mode, or a broken page: fall back / report.
        if layout:
            try:
                return "[layout mode failed, plain text follows]\n" + (page.extract_text() or "")
            except Exception as e2:  # noqa: BLE001
                return f"[text extraction failed: {e2}]"
        return f"[text extraction failed: {e}]"


def tidy_layout(text):
    """Keep column separation readable without hundreds of spaces per line."""
    out = []
    for line in text.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        out.append(WIDE_GAP.sub("  |  ", line))
    return "\n".join(out)


def do_layout(reader, pages, report):
    n = len(reader.pages)
    for p in pages:
        if p < 1 or p > n:
            report.add(f"!! page {p} out of range (document has {n} pages)")
            continue
        report.sub(f"page {p} of {n}")
        report.add(tidy_layout(page_text(reader.pages[p - 1], layout=True)))


def do_match(reader, pattern, report, neighbours=0, cap=6):
    rx = re.compile(pattern, re.I)
    n = len(reader.pages)
    hits = [i + 1 for i, pg in enumerate(reader.pages) if rx.search(page_text(pg))]
    if not hits:
        report.add(f"(no page matches /{pattern}/)")
        return
    wanted = []
    for h in hits:
        for p in range(h - neighbours, h + neighbours + 1):
            if 1 <= p <= n and p not in wanted:
                wanted.append(p)
    report.add(f"pages matching /{pattern}/: {hits}")
    if len(wanted) > cap:
        report.add(f"(showing first {cap} of {len(wanted)} pages)")
        wanted = wanted[:cap]
    do_layout(reader, wanted, report)


def do_grep(reader, pattern, report):
    rx = re.compile(pattern, re.I)
    found = 0
    for i, pg in enumerate(reader.pages):
        for line in page_text(pg).splitlines():
            if rx.search(line):
                report.add(f"p{i + 1} | {line.strip()}")
                found += 1
    if not found:
        report.add(f"(no line matches /{pattern}/)")


def do_dates(reader, report):
    found = 0
    for i, pg in enumerate(reader.pages):
        for line in page_text(pg).splitlines():
            if DATE_LINE.search(line):
                report.add(f"p{i + 1} | {line.strip()[:160]}")
                found += 1
                if found >= 25:
                    report.add("(first 25 date lines only)")
                    return
    if not found:
        report.add("(no line mentions a year 2019-2029)")


def do_fields(reader, report):
    try:
        fields = reader.get_fields() or {}
    except Exception as e:  # noqa: BLE001
        report.add(f"!! could not read form fields: {e}")
        return
    if not fields:
        report.add("(no interactive form fields)")
        return
    for name, f in fields.items():
        report.add(f"{name}: {f.get('/V', '')!s} (type {f.get('/FT', '')})")


def run_job(job, report):
    report.heading(f"{job['title']}  [{job['file']}]")
    reader = open_pdf(job["file"], report)
    if reader is None:
        return
    report.add(f"{len(reader.pages)} pages")
    for step in job["steps"]:
        kind = step[0]
        if kind == "layout":
            report.sub(f"layout of pages {step[1]}")
            do_layout(reader, step[1], report)
        elif kind == "match":
            opts = step[2] if len(step) > 2 else {}
            report.sub(f"pages matching /{step[1]}/")
            do_match(reader, step[1], report, **opts)
        elif kind == "grep":
            report.sub(f"lines matching /{step[1]}/")
            do_grep(reader, step[1], report)
        elif kind == "dates":
            report.sub("date lines")
            do_dates(reader, report)
        elif kind == "fields":
            report.sub("form fields")
            do_fields(reader, report)
        else:
            report.add(f"!! unknown step kind: {kind}")


# ---------------------------------------------------------------------------
# The checks. Paths are relative to data/provider-docs/.
# ---------------------------------------------------------------------------
CARD_LOAN = r"credit card|mortgage|home loan|personal loan|overdraft"

JOBS = [
    {
        "title": "Republic - tariff guide: mortgage fees (p7-8) and credit cards (p10)",
        "file": "republic-bank-ghana/TARIFF-GUIDE_MARCH2026-PUBLIC-V2.pdf",
        "steps": [
            ("dates",),
            ("layout", [7, 8, 10]),
            ("grep", r"\bFCL\b|\bRB\b|\bNRG\b|foreign currency loan|non[- ]resident|exclude taxes"),
        ],
    },
    {
        "title": "Republic - 2025 annual report: rates actually charged on mortgages",
        "file": "republic-bank-ghana/REPUBLIC-BANK-GHANA-ANNUAL-REPORT-2025.pdf",
        "steps": [
            ("match", r"Interest rate charge", {"neighbours": 1, "cap": 3}),
        ],
    },
    {
        "title": "First National - personal pricing guide",
        "file": "first-national-bank-ghana/FNBGH_Pricing_Guide.pdf",
        "steps": [
            ("dates",),
            ("match", CARD_LOAN, {"cap": 6}),
        ],
    },
    {
        "title": "Absa - tariff guide (retail)",
        "file": "absa-bank-ghana/tariff-guide.pdf",
        "steps": [
            ("dates",),
            ("match", CARD_LOAN, {"cap": 6}),
        ],
    },
    {
        "title": "Absa - tariff guide (Premier)",
        "file": "absa-bank-ghana/tariff-guide-premier.pdf",
        "steps": [
            ("dates",),
            ("match", CARD_LOAN, {"cap": 6}),
        ],
    },
    {
        "title": "Absa - tariff guide (corporate and business)",
        "file": "absa-bank-ghana/tariff-guide-corporate-and-business-banking.pdf",
        "steps": [
            ("dates",),
            ("match", CARD_LOAN, {"cap": 4}),
        ],
    },
    {
        "title": "Absa - daily rates",
        "file": "absa-bank-ghana/daily-rates.pdf",
        "steps": [
            ("dates",),
            ("layout", [1, 2]),
        ],
    },
    {
        "title": "Tesah - individual or joint account opening form",
        "file": "tesah-capital/Individual-or-Joint-Account-Opening-002.pdf",
        "steps": [
            ("dates",),
            ("grep", r"fee|management|charge|commission|%|per annum|discretion"),
            ("fields",),
        ],
    },
    {
        "title": "Tesah - institutional account form",
        "file": "tesah-capital/Institutional.pdf",
        "steps": [
            ("dates",),
            ("grep", r"fee|management|charge|commission|%|per annum|discretion"),
            ("fields",),
        ],
    },
]


def main():
    if not DOCS.exists():
        sys.exit(f"Not found: {DOCS} - run this from the repo root (C:\\Projects\\cediwise).")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = OUT_DIR / f"report_{stamp}.txt"

    report = Report()
    report.add(f"Cedafin document inspection - {datetime.now():%Y-%m-%d %H:%M}")
    report.add(f"Source folder: {DOCS}")
    for i, job in enumerate(JOBS, 1):
        print(f"[{i}/{len(JOBS)}] {job['title']}")
        run_job(job, report)

    out_path.write_text("\n".join(report.lines), encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"\nReport written: {out_path}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()

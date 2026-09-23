"""
load_provider_charges.py - load charges transcribed from provider documents.

Reads:
    data/provider-docs/provider_doc_fees_2026-09.csv               Republic, Absa, Tesah
    data/provider-docs/provider_doc_fees_first-atlantic_2026-08.csv First Atlantic (page 2 read from the page image)
    data/provider-docs/first-national-bank-ghana/fnb_homeloan_fees.csv   First National

Writes (only with --apply):
    sources            one row per document: kind, date, archive path, SHA-256
    provider_charges   one row per charge, with the document's own wording

Default is a DRY RUN: it validates everything, prints what it would write, and
writes nothing. Validation errors stop the run in either mode.

Re-running is safe: sources are matched by content SHA-256, and charges are
upserted on (source_id, charge_key, product_label).

Usage (repo root, venv active):
    python load_provider_charges.py            # dry run
    python load_provider_charges.py --apply    # write
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from cedafin_env import supabase_config

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "data" / "provider-docs"
SCANS = ROOT / "reports" / "scans" / "2026-09"

COMBINED_CSVS = [
    DOCS / "provider_doc_fees_2026-09.csv",
    DOCS / "provider_doc_fees_first-atlantic_2026-08.csv",
]
FNB_CSV = DOCS / "first-national-bank-ghana" / "fnb_homeloan_fees.csv"

READ_ON = "2026-09-23"   # the day these documents were read and transcribed

# One entry per document. document_date is the first of the month the document
# names; effective_note says so, so it is never mistaken for a stated day.
DOCUMENTS = {
    "TARIFF-GUIDE_MARCH2026-PUBLIC-V2.pdf": {
        "provider": "republic-bank-ghana",
        "folder": "republic-bank-ghana",
        "kind": "tariff_guide",
        "publisher": "Republic Bank (Ghana) PLC",
        "title": "Tariff Guide V2.0 (current update March 2026)",
        "document_date": "2026-03-01",
        "effective_note": "Document states 'CURRENT UPDATE MARCH 2026' (p12); stored as 1 March 2026. "
                          "All fees quoted exclude taxes (p11).",
    },
    "FNBGH_HomeLoans_Pricing_Guide.pdf": {
        "provider": "first-national-bank-ghana",
        "folder": "first-national-bank-ghana",
        "kind": "tariff_guide",
        "publisher": "First National Bank Ghana",
        "title": "Home Loans Pricing Guide (March 2026)",
        "document_date": "2026-03-01",
        "effective_note": "Document states 'March 2026' (p1); stored as 1 March 2026.",
    },
    "tariff-guide.pdf": {
        "provider": "absa-bank-ghana",
        "folder": "absa-bank-ghana",
        "kind": "tariff_guide",
        "publisher": "Absa Bank Ghana",
        "title": "Tariff Guide (September 2026)",
        "document_date": "2026-09-01",
        "effective_note": "Cover states 'September 2026' (p1); stored as 1 September 2026. "
                          "p3 also refers to charges that 'remain unchanged for 2025'.",
    },
    "tariff-guide-premier.pdf": {
        "provider": "absa-bank-ghana",
        "folder": "absa-bank-ghana",
        "kind": "tariff_guide",
        "publisher": "Absa Bank Ghana",
        "title": "Tariff Guide - Premier banking (September 2026)",
        "document_date": "2026-09-01",
        "effective_note": "Cover states 'September 2026' (p1); stored as 1 September 2026.",
    },
    "Tariff_Guide_24th_August_2026.pdf": {
        "provider": "first-atlantic-bank",
        "folder": "first-atlantic-bank",
        "kind": "tariff_guide",
        "publisher": "First Atlantic Bank PLC",
        "title": "Tariff Guide (24 August 2026)",
        "document_date": "2026-08-24",
        "effective_note": "The guide states no date; its file name ('Tariff_Guide_24th_August_2026') and PDF "
                          "metadata give 24 August 2026. Page 2 is an image: its figures were transcribed by "
                          "reading the page image, not extracted text. Rates quoted as a margin over the Ghana "
                          "Reference Rate (GRR) are stored as the margin; the GRR itself changes monthly.",
    },
    "Individual-or-Joint-Account-Opening-002.pdf": {
        "provider": "tesah-capital",
        "folder": "tesah-capital",
        "kind": "account_form",
        "publisher": "Tesah Capital",
        "title": "Individual or Joint Account Opening form (Investment Management Agreement)",
        "document_date": None,
        "effective_note": "The form's text states no date. PDF metadata: created 2021-05-08, "
                          "last modified 2021-05-10. Still offered on Tesah's website in September 2026.",
    },
}

CATEGORIES = {"mortgage", "credit_card", "personal_loan", "overdraft",
              "investment_management", "account", "other",
              "auto_loan", "business_loan", "guarantee", "savings"}
RATE_PERIODS = {"one_off", "year", "month", "per_transaction",
                "per_occurrence", "per_billing_cycle", "not_stated", "quarter"}

# Product names that describe a whole product line rather than one product; charges
# under them are stored with an empty product_label (as first loaded on 23 Sept).
GENERIC_PRODUCTS = {"mortgage", "personal loan", "current account", "individual/joint managed account"}
COLLECTED_FOR = {"bank", "manager", "government_stamp_duty",
                 "deposit_towards_registration", "not_stated"}

# First National's CSV has no period column; these are the charges that are not one-off.
FNB_PERIODS = {
    "late_payment": "year",            # 6% per annum above the borrower's rate, on arrears
    "default_interest": "year",
    "statement_hard_copy": "per_occurrence",
    "visa_letter": "per_occurrence",
    "document_copies": "per_occurrence",
    "clearance_letter": "per_occurrence",
    "confirmation_letter": "per_occurrence",
    "demand_letter": "per_occurrence",
}


# ----------------------------------------------------------------------------- helpers
def num(s: str | None) -> float | None:
    s = (s or "").strip()
    return float(s) if s else None


def minor(amount: float | None) -> int | None:
    return None if amount is None else int(round(amount * 100))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_urls() -> dict[str, str]:
    """Map PDF file name -> the URL the September scan downloaded it from."""
    urls: dict[str, str] = {}
    for f in sorted(SCANS.glob("*_documents.csv")):
        with open(f, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                name = Path((row.get("file") or "").replace("\\", "/")).name
                if name and row.get("document"):
                    urls.setdefault(name, row["document"])
    return urls


# ----------------------------------------------------------------------------- REST
class Rest:
    def __init__(self):
        self.base, key = supabase_config()
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _call(self, method: str, path: str, body=None, extra: dict | None = None):
        req = urllib.request.Request(
            f"{self.base}/{path}",
            method=method,
            data=None if body is None else json.dumps(body).encode("utf-8"),
            headers={**self.headers, **(extra or {})},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            sys.exit(f"\n!! {method} {path.split('?')[0]} failed ({e.code}): {detail}")

    def get(self, path: str):
        return self._call("GET", path)

    def insert(self, table: str, rows, upsert_on: str | None = None):
        path = table
        prefer = "return=representation"
        if upsert_on:
            path += "?on_conflict=" + urllib.parse.quote(upsert_on)
            prefer += ",resolution=merge-duplicates"
        return self._call("POST", path, rows, {"Prefer": prefer})


# ----------------------------------------------------------------------------- rows
def rows_from_combined() -> list[dict]:
    out = []
    for path in COMBINED_CSVS:
      with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            category = r["category"].strip()
            # A named product keeps its name; a whole product line gets an empty label.
            product = r["product"].strip()
            label = "" if product.lower() in GENERIC_PRODUCTS else product
            out.append({
                "source_file": r["source_file"].strip(),
                "provider": r["provider"].strip(),
                "category": category,
                "product_label": label,
                "charge_key": r["fee_key"].strip(),
                "charge_name": r["fee_name"].strip(),
                "applies_when": r["applies_when"].strip() or None,
                "rate": num(r["rate"]),
                "rate_period": r["rate_period"].strip() or None,
                "rate_basis": r["rate_basis"].strip() or None,
                "flat_minor": minor(num(r["fixed_amount"])),
                "flat_currency": r["currency"].strip() or None,
                "limit_note": r["minimum_or_cap"].strip() or None,
                "collected_for": r["collected_for"].strip() or "not_stated",
                "wording": r["document_wording"].strip(),
                "page": int(r["page"]) if r["page"].strip() else None,
            })
    return out


def rows_from_fnb() -> list[dict]:
    out = []
    with open(FNB_CSV, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            key = r["fee_key"].strip()
            usd_fixed, ghs_fixed = num(r["fixed_usd"]), num(r["fixed_ghs"])
            flat, cur = (usd_fixed, "USD") if usd_fixed is not None else (ghs_fixed, "GHS" if ghs_fixed is not None else None)
            min_usd = num(r["minimum_usd"])
            usd_t, ghs_t = r["usd_terms"].strip(), r["ghs_terms"].strip()
            wording = usd_t if ghs_t in ("", "same", usd_t) else f"USD: {usd_t} | GHS: {ghs_t}"
            rate = num(r["rate"])
            period = FNB_PERIODS.get(key, "one_off" if (rate is not None or flat is not None) else None)
            basis = r["rate_basis"].strip() or None
            if basis == "per_annum_above_borrower_rate_on_arrears":
                basis = "above_borrower_rate_on_arrears"
            out.append({
                "source_file": r["source_file"].strip(),
                "provider": "first-national-bank-ghana",
                "category": "mortgage",
                "product_label": "",
                "charge_key": key,
                "charge_name": r["fee_name"].strip(),
                "applies_when": r["applies_when"].strip() or None,
                "rate": rate,
                "rate_period": period,
                "rate_basis": basis,
                "flat_minor": minor(flat),
                "flat_currency": cur if flat is not None else None,
                "limit_note": (f"min USD {min_usd:g} (GHS schedule: GHS equivalent of USD {min_usd:g})"
                               if min_usd is not None else None),
                "collected_for": r["collected_for"].strip() or "not_stated",
                "wording": wording,
                "page": int(r["page"]) if r["page"].strip() else None,
            })
    return out


def validate(rows: list[dict]) -> list[str]:
    errs, seen = [], set()
    for i, r in enumerate(rows, 1):
        where = f"row {i} [{r['source_file']} / {r['charge_key']} / {r['product_label'] or '-'}]"
        if r["source_file"] not in DOCUMENTS:
            errs.append(f"{where}: document not listed in DOCUMENTS")
        if r["category"] not in CATEGORIES:
            errs.append(f"{where}: category '{r['category']}' not allowed")
        if r["rate_period"] is not None and r["rate_period"] not in RATE_PERIODS:
            errs.append(f"{where}: rate_period '{r['rate_period']}' not allowed")
        if r["collected_for"] not in COLLECTED_FOR:
            errs.append(f"{where}: collected_for '{r['collected_for']}' not allowed")
        if r["rate"] is not None and not (0 <= r["rate"] <= 1):
            errs.append(f"{where}: rate {r['rate']} outside 0-1 (percentages must be fractions)")
        if r["flat_minor"] is not None and not r["flat_currency"]:
            errs.append(f"{where}: fixed amount with no currency")
        if not r["wording"]:
            errs.append(f"{where}: no document wording")
        k = (r["source_file"], r["charge_key"], r["product_label"])
        if k in seen:
            errs.append(f"{where}: duplicate of an earlier row (same document, key and label)")
        seen.add(k)
    return errs


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write to the database (default: dry run)")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY RUN - nothing will be written"
    print(f"load_provider_charges.py  [{mode}]\n")

    for f in (*COMBINED_CSVS, FNB_CSV):
        if not f.exists():
            sys.exit(f"!! missing input: {f}")

    rows = rows_from_combined() + rows_from_fnb()
    errs = validate(rows)

    # Documents: file present, fingerprint, scan URL
    urls = scan_urls()
    docs: dict[str, dict] = {}
    for name, meta in DOCUMENTS.items():
        path = DOCS / meta["folder"] / name
        if not path.exists():
            errs.append(f"document file not found: {path}")
            continue
        docs[name] = {
            **meta,
            "path": path,
            "storage_path": f"data/provider-docs/{meta['folder']}/{name}",
            "sha256": sha256(path),
            "url": urls.get(name),
            "retrieved_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        }

    if errs:
        print("VALIDATION FAILED - nothing written:")
        for e in errs:
            print("  -", e)
        sys.exit(1)

    rest = Rest()

    # Providers must already exist
    slugs = sorted({d["provider"] for d in DOCUMENTS.values()})
    found = rest.get("providers?select=id,slug&slug=in.(" + ",".join(slugs) + ")") or []
    provider_ids = {p["slug"]: p["id"] for p in found}
    missing = [s for s in slugs if s not in provider_ids]
    if missing:
        sys.exit(f"!! providers not in the database: {missing} - nothing written")

    # Report per document
    by_doc: dict[str, list[dict]] = {}
    for r in rows:
        by_doc.setdefault(r["source_file"], []).append(r)

    for name, d in docs.items():
        existing = rest.get("sources?select=id&content_sha256=eq." + d["sha256"]) or []
        d["source_id"] = existing[0]["id"] if existing else None
        n = len(by_doc.get(name, []))
        cats = sorted({r["category"] for r in by_doc.get(name, [])})
        print(f"{d['provider']:28} {name}")
        print(f"    kind={d['kind']}  date={d['document_date'] or 'none stated'}  sha256={d['sha256'][:12]}...")
        print(f"    url={d['url'] or 'NOT IN SCAN LOGS'}")
        print(f"    source row: {'exists (' + d['source_id'][:8] + ')' if d['source_id'] else 'NEW'}")
        print(f"    charges: {n}  categories: {', '.join(cats)}")
    print(f"\nTotal charges: {len(rows)}")

    print("\nSample rows:")
    for r in rows[:3] + [r for r in rows if r["category"] == "credit_card"][:2] + [r for r in rows if r["provider"] == "tesah-capital"]:
        amount = f"{r['flat_minor'] / 100:g} {r['flat_currency']}" if r["flat_minor"] is not None else ""
        rate = f"{r['rate'] * 100:g}%" if r["rate"] is not None else ""
        print(f"  {r['provider']:26} {r['category']:22} {r['product_label'] or '-':28} "
              f"{r['charge_key']:26} {rate:>7} {amount:>12}  {r['rate_period'] or ''}")

    if not args.apply:
        print("\nDry run complete. Re-run with --apply to write.")
        return

    # ---- write: sources first, then charges
    for name, d in docs.items():
        if d["source_id"]:
            continue
        created = rest.insert("sources", [{
            "kind": d["kind"],
            "publisher": d["publisher"],
            "title": d["title"],
            "url": d["url"],
            "document_date": d["document_date"],
            "retrieved_at": d["retrieved_at"],
            "storage_path": d["storage_path"],
            "content_sha256": d["sha256"],
        }])
        d["source_id"] = created[0]["id"]
        print(f"  + source {name} -> {d['source_id'][:8]}")

    payload = []
    for r in rows:
        d = docs[r["source_file"]]
        payload.append({
            "provider_id": provider_ids[r["provider"]],
            "category": r["category"],
            "product_label": r["product_label"],
            "charge_key": r["charge_key"],
            "charge_name": r["charge_name"],
            "applies_when": r["applies_when"],
            "rate": r["rate"],
            "rate_period": r["rate_period"],
            "rate_basis": r["rate_basis"],
            "flat_minor": r["flat_minor"],
            "flat_currency": r["flat_currency"],
            "limit_note": r["limit_note"],
            "collected_for": r["collected_for"],
            "wording": r["wording"],
            "page": r["page"],
            "source_id": d["source_id"],
            "effective_from": d["document_date"],
            "effective_note": d["effective_note"],
            "verified_on": READ_ON,
        })
    written = rest.insert("provider_charges", payload, upsert_on="source_id,charge_key,product_label")
    print(f"\nWrote {len(written or [])} charges.")


if __name__ == "__main__":
    main()

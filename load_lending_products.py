"""
load_lending_products.py — bank lending as comparable products.

ONE PRODUCT PER BANK PER CATEGORY PER TENOR
Standard Chartered's 1-year SME facility is a different product from its 5-year
one — different rate, different term, different answer for a borrower. So 23
banks across 9 category/tenor combinations gives up to 207 products, not 23.

That mirrors the investment side, where Stanbic Cash Trust's two share classes
are two rows because they return 36.88% and 14.04%.

WHAT GOES WHERE, and why the borrow side reuses the invest schema:

    rate_min / rate_max   the average lending rate and the average APR.
                          NOT a quoted range — see below.
    rate_basis            'apr' — annualised, fees included
    lock_in_days          the tenor
    eligibility_notes     BoG's own indicative caveat, verbatim
    product_fees          commitment, processing, arrangement, insurance,
                          facility — each its own row, as on the fund side

WHY rate_min IS THE LENDING RATE AND rate_max IS THE APR
BoG publishes one average lending rate and one average APR per bank per table,
not a range of offers. Absa's household loan lends at 16.93% and its APR is
18.32% — the difference is processing and insurance fees. Storing those as
min and max is honest about what a borrower faces: the advertised rate at best,
the true cost in practice. A single figure would hide the gap, and the gap is
the point.

INDICATIVE IS NOT A FOOTNOTE
BoG states that a typical customer may face an actual APR different from these,
depending on the bank's assessment. Every product carries that in
eligibility_notes, and nothing here should reach a page without it. Publishing
11.03% as what a business WILL get would be wrong in the direction that costs
someone money.

Usage:
    python load_lending_products.py --dry-run
    python load_lending_products.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request

CATEGORY_LABEL = {
    "household": "Personal loan",
    "sme": "SME loan",
    "corporate": "Corporate loan",
}
ASSET_CLASS = {
    "household": "personal_credit",
    "sme": "sme_credit",
    "corporate": "corporate_credit",
}

INDICATIVE = (
    "Indicative rate published by Bank of Ghana. A typical customer may be "
    "offered a different APR depending on the bank's assessment of their "
    "circumstances. This is not a quote."
)


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
HDRS = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json", "Prefer": "return=representation"}


def rest(method: str, path: str, body=None, prefer: str | None = None) -> list:
    h = dict(HDRS)
    if prefer:
        h["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}\n  "
                           f"{e.read().decode('utf-8', 'replace')[:300]}") from e


def slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def short_name(bank: str) -> str:
    """'Absa Bank Ghana Limited' -> 'Absa Bank Ghana' for display."""
    s = re.sub(r"\s+(Limited|Ltd|PLC|Plc)\.?$", "", bank).strip()
    return s or bank


def num(v) -> float | None:
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--banks-csv", default="apr_banks.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.banks_csv):
        print(f"{args.banks_csv} not found — run extract_apr.py first.")
        return 1
    rows = list(csv.DictReader(open(args.banks_csv, encoding="utf-8")))
    if not rows:
        print("No rows.")
        return 1

    # Only the most recent report per bank/category/tenor becomes a product.
    # Older reports are history and belong in a rate series, not in a second
    # product for the same facility.
    latest = max(r["as_of"] for r in rows)
    current = [r for r in rows if r["as_of"] == latest]
    print(f"{len(rows)} rows across all reports; {len(current)} at {latest}\n")

    banks = sorted({r["bank"] for r in current})
    combos: dict[tuple[str, str], list] = {}
    for r in current:
        combos.setdefault((r["category"], r["tenor_years"]), []).append(r)

    print(f"  {len(banks)} banks, {len(combos)} category/tenor combinations")
    for (cat, tenor), rs in sorted(combos.items()):
        aprs = [num(x["average_apr"]) for x in rs]
        aprs = [a for a in aprs if a is not None]
        if aprs:
            print(f"    {tenor}-yr {CATEGORY_LABEL[cat]:<16} {len(rs):>2} banks  "
                  f"{min(aprs):5.2f}% to {max(aprs):5.2f}%")

    if args.dry_run:
        print(f"\nWould create up to {len(banks)} providers and "
              f"{len(current)} products.")
        print("Dry run — nothing written.")
        return 0

    # Providers. A bank may already exist from the invest side — Stanbic sells
    # funds AND lends — so match on slug before creating.
    existing = rest("GET", "/providers?select=id,slug")
    by_slug = {p["slug"]: p["id"] for p in existing}
    prov: dict[str, str] = {}
    made_p = 0
    for bank in banks:
        slug = slugify(short_name(bank))
        if slug in by_slug:
            prov[bank] = by_slug[slug]
            continue
        prov[bank] = rest("POST", "/providers", {
            "slug": slug, "legal_name": bank, "trading_name": short_name(bank),
            "status": "published",
        })[0]["id"]
        by_slug[slug] = prov[bank]
        made_p += 1
    print(f"\n  {made_p} provider(s) created, "
          f"{len(banks) - made_p} already existed")

    # One source row for the report the figures came from.
    src_title = current[0]["source"]
    found = rest("GET", f"/sources?title=eq.{urllib.parse.quote(src_title)}&select=id")
    source_id = found[0]["id"] if found else rest("POST", "/sources", {
        "kind": "regulator_publication", "publisher": "Bank of Ghana",
        "title": src_title,
    })[0]["id"]

    have = {p["slug"] for p in rest("GET", "/products?select=slug")}
    made = 0
    fee_rows: list[dict] = []

    for r in current:
        bank, cat, tenor = r["bank"], r["category"], int(r["tenor_years"])
        lending = num(r["avg_lending_rate"])
        apr = num(r["average_apr"])
        if apr is None:
            continue

        slug = f"{slugify(short_name(bank))}-{cat}-{tenor}yr"
        if slug in have:
            continue

        pid = rest("POST", "/products", {
            "slug": slug,
            "provider_id": prov[bank],
            "name": f"{CATEGORY_LABEL[cat]}, {tenor} year"
                    f"{'s' if tenor > 1 else ''}",
            "share_class": "main",
            "market_side": "borrow",
            "legal_structure": "bank_loan",
            "asset_class": ASSET_CLASS[cat],
            "currency": "GHS",
            "lock_in_days": tenor * 365,
            "dealing_frequency": "on_application",
            # Lending rate at best, APR in practice. The gap is the fees.
            "rate_min": round((lending if lending is not None else apr) / 100, 8),
            "rate_max": round(apr / 100, 8),
            "rate_basis": "apr",
            "eligibility_notes": INDICATIVE,
            "distributes": False,
            "status": "published",
        })[0]["id"]
        made += 1

        # Fees as their own rows, same as the fund side. BoG gives a total of
        # the maxima rather than a breakdown per fee type in the extract, so
        # this records what is known and says what it is.
        total = num(r.get("max_fees_total"))
        if total:
            fee_rows.append({
                "product_id": pid, "fee_type": "other", "rate": round(total / 100, 8),
                "basis": "annual_nav",
                "conditions": f"Sum of up to {r.get('fee_count', '?')} maximum "
                              f"charges (commitment, processing, arrangement, "
                              f"insurance, facility). Already included in the "
                              f"APR; shown to separate headline rate from cost.",
                "effective_from": r["as_of"], "effective_to": None,
                "source_id": source_id, "verified_on": r["as_of"],
            })

    for i in range(0, len(fee_rows), 50):
        rest("POST", "/product_fees", fee_rows[i : i + 50], prefer="return=minimal")

    print(f"  {made} lending product(s) created, {len(fee_rows)} fee row(s)")
    print("\n  Every product carries BoG's indicative caveat in")
    print("  eligibility_notes. A page showing a rate without it would be")
    print("  telling a business what it will pay, which nobody knows.")
    print("\n  BANKS ONLY. Microfinance, savings and loans, and digital")
    print("  lenders are absent — and that is where SMEs refused by banks")
    print("  actually borrow.")
    return 0


if __name__ == "__main__":
    import urllib.parse  # noqa: E402
    sys.exit(main())

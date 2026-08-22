"""
load_to_supabase.py — turn the extracted CSVs into provenanced database rows.

WHAT THIS IS NOT: a CSV import. Every published number has to trace back to the
document it came from, which is the whole proposition (ARCHITECTURE.md §4).
So the order is: sources -> providers -> products -> fees -> observations, and
nothing lands without a source_id.

WHAT IT ENCODES, all of it learned from real data today:

  SHARE CLASSES  Stanbic Cash Trust main returned 36.88% over one year while
                 its AMC sub-class returned 14.04% — bonds versus fixed
                 deposits. Separate product rows under the unique index on
                 (provider_id, name, share_class). One row cannot hold both.

  series_kind    FAAM and PDIF publish a unit PRICE (quoted). The older Stanbic
                 files publish monthly RETURNS, so their series is an index
                 chained from those (chained), base 100. Volatility and
                 drawdown are valid on both; the LEVEL of a chained series is
                 not a dealing price and must never render as one.

  TER IS YTD     Every expense ratio extracted is year-to-date, not annualised
                 — the Stanbic files label it "(YTD Jun-25)" outright and the
                 values climb through each year. Loaded with effective_from set
                 to the observation date and a conditions note saying so.

  REVIEW FLAGS   Rows the extractor flagged are loaded but the product stays in
                 'draft'. Nothing reaches 'published' from a script.

Everything lands as status='draft'. Publishing is a human decision.

Usage:
    python load_to_supabase.py --dry-run     # show what would happen
    python load_to_supabase.py               # load
    python load_to_supabase.py --reset       # delete loaded rows, start over
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime

# --- provider and product mapping -------------------------------------------
# Derived from the fund names printed INSIDE the PDFs, not from filenames.
# Filenames and titles disagreed with contents more than once today.

PROVIDERS = {
    "stanbic": {
        "slug": "stanbic-investment-management-services",
        "legal_name": "Stanbic Investment Management Services LTD",
        "trading_name": "SIMS",
        "website": "https://www.sims.com.gh",
        "custodian": "Standard Chartered Bank Ghana PLC",
    },
    "faam": {
        "slug": "first-atlantic-asset-management",
        "legal_name": "First Atlantic Asset Management Company Limited",
        "trading_name": "FAAM",
        "website": "https://faam.com.gh",
        "custodian": "GT Bank (GH) Ltd.",
    },
}

# fund_key from the extractor -> product definition
PRODUCTS = {
    "PDIF_Fact_Sheet::main": {
        "provider": "stanbic", "slug": "platinum-debt-income-fund",
        "name": "Platinum Debt Income Fund PLC", "share_class": "main",
        "share_class_label": None, "asset_class": "fixed_income",
        "legal_structure": "mutual_fund", "distributes": True,
        "dealing_frequency": "daily",
        "note": "Distributes income — a NAV fall can be a payout, not a loss.",
    },
    "Stanbic_Cash_Trust_Fact_Sheet::main": {
        "provider": "stanbic", "slug": "stanbic-cash-trust",
        "name": "Stanbic Cash Trust", "share_class": "main",
        "share_class_label": "Main Class", "asset_class": "money_market",
        "legal_structure": "unit_trust", "distributes": False,
        "dealing_frequency": "daily",
        "note": "Reinvests earnings, so price return equals total return.",
    },
    "Stanbic_Cash_Trust_Fact_Sheet::sub": {
        "provider": "stanbic", "slug": "stanbic-cash-trust",
        "name": "Stanbic Cash Trust", "share_class": "sub",
        "share_class_label": "AMC Sub-Class", "asset_class": "money_market",
        "legal_structure": "unit_trust", "distributes": False,
        "dealing_frequency": "daily",
        "note": "Fixed deposits and money market; introduced December 2022.",
    },
    "Stanbic_Income_Fund_Trust_Fact_Sheet::main": {
        "provider": "stanbic", "slug": "stanbic-income-fund-trust",
        "name": "Stanbic Income Fund Trust", "share_class": "main",
        "share_class_label": "SIFT", "asset_class": "fixed_income",
        "legal_structure": "unit_trust", "distributes": False,
        "dealing_frequency": "daily", "note": "",
    },
    "Stanbic_Income_Fund_Trust_Fact_Sheet::sub": {
        "provider": "stanbic", "slug": "stanbic-income-fund-trust",
        "name": "Stanbic Income Fund Trust", "share_class": "sub",
        "share_class_label": "SIFTAMC", "asset_class": "fixed_income",
        "legal_structure": "unit_trust", "distributes": False,
        "dealing_frequency": "daily", "note": "",
    },
    "faam_faif::main": {
        "provider": "faam", "slug": "first-atlantic-income-fund",
        "name": "First Atlantic Income Fund", "share_class": "main",
        "share_class_label": "FAIF", "asset_class": "fixed_income",
        "legal_structure": "mutual_fund", "distributes": False,
        "dealing_frequency": "daily", "note": "",
    },
    "faam_pips::main": {
        "provider": "faam", "slug": "first-atlantic-personal-investment-plan",
        "name": "First Atlantic Personal Investment Plan", "share_class": "main",
        "share_class_label": "PIPS", "asset_class": "balanced",
        "legal_structure": "mutual_fund", "distributes": False,
        "dealing_frequency": "daily", "note": "",
    },
}


def env() -> dict:
    if not os.path.exists(".env.local"):
        print("No .env.local found — run from the project root.")
        sys.exit(1)
    out = {}
    for line in open(".env.local", encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    for need in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if not out.get(need):
            print(f"{need} is missing from .env.local")
            sys.exit(1)
    return out


E = env()
BASE = E["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = E["SUPABASE_SERVICE_ROLE_KEY"]
HDRS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


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
        detail = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"{method} {path} -> {e.code}\n  {detail}") from e


def sha256_of(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_pdf(filename: str) -> str | None:
    for root, _dirs, files in os.walk("data"):
        if filename in files:
            return os.path.join(root, filename)
    return None


def pesewas(amount) -> int | None:
    """Money is stored as bigint minor units. Never floats."""
    if amount in (None, "", "None"):
        return None
    try:
        return int(round(float(amount) * 100))
    except (TypeError, ValueError):
        return None


def dec(value) -> float | None:
    """Percentages are stored as decimals: 1.50% -> 0.015."""
    if value in (None, "", "None"):
        return None
    try:
        return round(float(value) / 100.0, 8)
    except (TypeError, ValueError):
        return None


def num(value) -> float | None:
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load(navs_csv: str, dry: bool) -> int:
    rows = list(csv.DictReader(open(navs_csv, encoding="utf-8")))
    if not rows:
        print(f"{navs_csv} is empty")
        return 1

    # group by the extractor's fund key
    def key_of(r: dict) -> str:
        import re
        stem = re.sub(r"_?-?_?\d{4}-\d{2}\.pdf$", "", r["file"]).strip("_-. ")
        return f"{stem}::{r.get('share_class', 'main')}"

    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(key_of(r), []).append(r)

    unknown = [k for k in grouped if k not in PRODUCTS]
    if unknown:
        print("Unmapped fund keys — add them to PRODUCTS before loading:")
        for k in unknown:
            print(f"    {k}   ({len(grouped[k])} rows)")
        return 1

    print(f"{len(rows)} observations across {len(grouped)} product/class rows\n")
    if dry:
        for k, rs in sorted(grouped.items()):
            p = PRODUCTS[k]
            navs = [r for r in rs if num(r.get("nav")) is not None]
            chained = [r for r in rs if num(r.get("period_return_pct")) is not None]
            kind = "quoted" if len(navs) >= len(chained) else "chained"
            flagged = sum(1 for r in rs if str(r.get("review_required")).lower() == "true")
            print(f"  {p['name']} [{p['share_class']}]")
            print(f"      {len(rs)} rows, series_kind={kind}, "
                  f"{flagged} flagged for review")
        print("\nDry run — nothing written.")
        return 0

    # 1. providers -------------------------------------------------------
    prov_ids: dict[str, str] = {}
    for pk, pv in PROVIDERS.items():
        got = rest("GET", f"/providers?slug=eq.{pv['slug']}&select=id")
        if got:
            prov_ids[pk] = got[0]["id"]
            print(f"  provider exists: {pv['trading_name']}")
        else:
            made = rest("POST", "/providers", {
                "slug": pv["slug"], "legal_name": pv["legal_name"],
                "trading_name": pv["trading_name"], "website": pv["website"],
                "custodian": pv["custodian"], "status": "draft",
            })
            prov_ids[pk] = made[0]["id"]
            print(f"  provider created: {pv['trading_name']}")

    # 2. sources — one per distinct PDF, with its hash --------------------
    src_ids: dict[str, str] = {}
    files = sorted({r["file"] for r in rows})
    print(f"\n  hashing {len(files)} document(s)...")
    for fname in files:
        path = find_pdf(fname)
        digest = sha256_of(path) if path else None
        if digest:
            got = rest("GET", f"/sources?content_sha256=eq.{digest}&select=id")
            if got:
                src_ids[fname] = got[0]["id"]
                continue
        made = rest("POST", "/sources", {
            "kind": "provider_factsheet",
            "publisher": "SIMS" if fname.lower().startswith(("stanbic", "pdif"))
                         else "FAAM",
            "title": fname,
            "storage_path": path.replace("\\", "/") if path else None,
            "content_sha256": digest,
        })
        src_ids[fname] = made[0]["id"]
    print(f"  {len(src_ids)} source row(s)")

    # 3. products, fees, observations -------------------------------------
    total_obs = total_fees = 0
    for k, rs in sorted(grouped.items()):
        p = PRODUCTS[k]
        rs.sort(key=lambda r: r["as_of"])
        latest = rs[-1]

        navs = [r for r in rs if num(r.get("nav")) is not None]
        chained = [r for r in rs if num(r.get("period_return_pct")) is not None]
        kind = "quoted" if len(navs) >= len(chained) else "chained"

        existing = rest("GET", f"/products?slug=eq.{p['slug']}"
                               f"&share_class=eq.{p['share_class']}&select=id")
        if existing:
            pid = existing[0]["id"]
        else:
            body = {
                "slug": p["slug"], "provider_id": prov_ids[p["provider"]],
                "name": p["name"], "share_class": p["share_class"],
                "share_class_label": p["share_class_label"],
                "legal_structure": p["legal_structure"],
                "asset_class": p["asset_class"], "currency": "GHS",
                "distributes": p["distributes"],
                "distribution_note": p["note"] or None,
                "dealing_frequency": p["dealing_frequency"],
                "min_initial_minor": pesewas(latest.get("min_investment")),
                "min_source_id": src_ids.get(latest["file"]),
                "min_verified_on": latest["as_of"],
                "status": "draft",
            }
            # slug collides across share classes by design; the unique index is
            # (provider_id, name, share_class), so a second class needs a
            # distinct slug for the URL.
            if p["share_class"] != "main":
                body["slug"] = f"{p['slug']}-{p['share_class']}"
            pid = rest("POST", "/products", body)[0]["id"]

        # fees — the TER is YTD, and that must travel with the number
        fees = []
        if dec(latest.get("management_fee_pct")) is not None:
            fees.append({"product_id": pid, "fee_type": "management",
                         "rate": dec(latest["management_fee_pct"]),
                         "basis": "annual_nav",
                         "effective_from": latest["as_of"],
                         "source_id": src_ids[latest["file"]],
                         "verified_on": latest["as_of"]})
        if dec(latest.get("trustee_or_custody_fee_pct")) is not None:
            fees.append({"product_id": pid, "fee_type": "custody",
                         "rate": dec(latest["trustee_or_custody_fee_pct"]),
                         "basis": "annual_nav",
                         "effective_from": latest["as_of"],
                         "source_id": src_ids[latest["file"]],
                         "verified_on": latest["as_of"]})
        if dec(latest.get("ter_pct")) is not None:
            fees.append({"product_id": pid, "fee_type": "ter",
                         "rate": dec(latest["ter_pct"]),
                         "basis": "annual_nav",
                         "conditions": "YEAR-TO-DATE as published, NOT annualised "
                                       "— do not compare directly against an "
                                       "annual TER",
                         "effective_from": latest["as_of"],
                         "source_id": src_ids[latest["file"]],
                         "verified_on": latest["as_of"]})
        if fees:
            # PostgREST requires EVERY object in a bulk insert to have the
            # same keys — the TER row carries a `conditions` note the others
            # do not, which returns PGRST102 "All object keys must match".
            # Normalise to the union of keys, filling the rest with None.
            all_keys = sorted({k for f in fees for k in f})
            fees = [{k: f.get(k) for k in all_keys} for f in fees]
            rest("POST", "/product_fees", fees)
            total_fees += len(fees)

        # observations
        obs = []
        level = 100.0
        for r in rs:
            nav = num(r.get("nav"))
            pr = num(r.get("period_return_pct"))
            if kind == "quoted":
                if nav is None:
                    continue
                value = nav
            else:
                if pr is None:
                    continue
                level *= (1.0 + pr / 100.0)
                value = round(level, 6)
            obs.append({
                "product_id": pid, "as_of": r["as_of"], "nav": value,
                "basis": "single", "series_kind": kind,
                "period_return": dec(pr) if pr is not None else None,
                "source_id": src_ids[r["file"]],
            })
        if obs:
            rest("POST", "/nav_observations", obs,
                 prefer="return=minimal,resolution=ignore-duplicates")
            total_obs += len(obs)

        flagged = sum(1 for r in rs if str(r.get("review_required")).lower() == "true")
        print(f"  {p['name'][:38]:<40} {p['share_class']:<5} "
              f"{len(obs):>3} obs  {kind:<8} {flagged} flagged")

    print(f"\n  {total_obs} observations, {total_fees} fee rows")
    print("  Everything is status='draft'. Nothing publishes from a script.")
    return 0


def reset() -> int:
    print("Deleting loaded rows...")
    for table in ("nav_observations", "product_fees", "products",
                  "sources", "providers"):
        rest("DELETE", f"/{table}?id=not.is.null" if table != "nav_observations"
             else "/nav_observations?id=gt.0", prefer="return=minimal")
        print(f"  cleared {table}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--navs", default="navs.csv")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    if args.reset:
        return reset()
    return load(args.navs, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())

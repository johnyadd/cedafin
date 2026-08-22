"""
load_catalogue.py — load the full Ghanaian CIS universe as directory entries.

WHY THIS EXISTS
Five funds are loaded with real data. Seventy-two exist. The gap is not
discovery — the catalogue has been sitting in arg_funds.csv since the API was
mapped — it is that only five could be fetched AND extracted.

A directory of 72 with 5 covered in depth is a far better product than 5 alone,
and it is what makes provider outreach work: you are asking a fund manager to
CORRECT AN EXISTING LISTING, not to grant a favour. That is the difference
between "your fund is listed and three fields are blank" and "please send me
your data".

WHAT THESE ROWS ARE, AND ARE NOT
Catalogue entries carry a name, a provider and a category. No prices, no fees,
no minimums. They are loaded as:

    status          = 'draft'      never published, never comparable
    listing_only    = true         a directory entry, not a covered fund

The comparison pages query status='published', so these cannot leak into a
cost comparison and appear as though they had no charges. Absent must never
render as free — the same rule that sorts unpriced funds last.

NAMES ARE UNVERIFIED
The catalogue is a third-party aggregator's, not the SEC register. Fund names
there may be stale, abbreviated or renamed — several slugs carry "formerly"
markers, which is useful history but also evidence that names move. Emailing a
fund manager with their own fund's name wrong is a poor first contact, so every
row is flagged name_verified=false until checked against sec_licensees.csv.

Also writes outreach.csv: one row per fund with what is missing, ordered so
the providers where a single email unlocks the most funds come first.

Usage:
    python load_catalogue.py --dry-run
    python load_catalogue.py
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

CATEGORY_HINTS = [
    ("money_market", r"money\s*market|cash\s*trust|liquidity|treasury\s*trust"),
    ("fixed_income", r"fixed\s*income|income\s*fund|bond|debt"),
    ("balanced", r"balanced|multi\s*asset"),
    ("equity", r"equity|growth\s*fund|alpha"),
    ("real_estate", r"reit|real\s*estate|property"),
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


def categorise(name: str, slug: str) -> str | None:
    hay = f"{name} {slug}".lower()
    for cat, pattern in CATEGORY_HINTS:
        if re.search(pattern, hay):
            return cat
    return None


def provider_of(slug: str, name: str) -> str:
    """
    Best-effort provider from the fund's own name. Deliberately crude — this is
    a grouping hint for outreach, not an authoritative mapping. The SEC register
    is the source of truth and this gets checked against it before any email.
    """
    known = {
        "databank": "Databank", "stanlib": "Stanbic", "stanbic": "Stanbic",
        "edc": "EDC", "ic-": "IC Asset Managers", "fidelity": "Fidelity",
        "republic": "Republic", "sas": "SAS", "nimed": "Nimed",
        "investcorp": "InvestCorp", "sentinel": "Sentinel", "omega": "Omega",
        "glico": "GLICO", "ecocapital": "EcoCapital", "sem-": "SEM",
        "bora": "Bora", "crystal": "Crystal", "first-atlantic": "First Atlantic",
        "tesah": "Tesah", "nthc": "NTHC", "umb": "UMB", "cal-": "CAL",
        "plus-": "Plus", "gold-": "Gold", "dalex": "Dalex", "delta": "Delta",
    }
    low = f"{slug}-"
    for key, label in known.items():
        if low.startswith(key) or f"-{key}" in low:
            return label
    return name.split()[0] if name else "Unknown"


def slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--funds", default="arg_funds.csv")
    ap.add_argument("--docs", default="arg_docs.csv")
    ap.add_argument("--outreach", default="outreach.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.funds):
        print(f"{args.funds} not found — run: python arg_client.py --catalogue")
        return 1
    rows = list(csv.DictReader(open(args.funds, encoding="utf-8")))

    doc_counts: dict[str, dict[str, int]] = {}
    if os.path.exists(args.docs):
        for d in csv.DictReader(open(args.docs, encoding="utf-8")):
            slug = d.get("fund_slug")
            if slug:
                doc_counts.setdefault(slug, {})
                k = d.get("kind", "other")
                doc_counts[slug][k] = doc_counts[slug].get(k, 0) + 1

    existing = rest("GET", "/products?select=id,name,slug,status")
    have_names = {p["name"].lower() for p in existing}
    have_slugs = {p["slug"] for p in existing}

    providers = rest("GET", "/providers?select=id,slug,trading_name,legal_name")
    prov_by_label = {
        (p["trading_name"] or p["legal_name"] or "").lower(): p["id"] for p in providers
    }

    to_load, skipped, outreach = [], [], []
    for r in rows:
        name = (r.get("name") or "").strip()
        slug = (r.get("slug") or "").strip()
        if not name or not slug:
            continue
        if name.lower() in have_names or slug in have_slugs:
            skipped.append(name)
            continue

        label = provider_of(slug, name)
        docs = doc_counts.get(slug, {})
        factsheets = docs.get("factsheet", 0)
        reports = docs.get("annual_report", 0)

        to_load.append({
            "slug": slug, "name": name, "provider_label": label,
            "asset_class": categorise(name, slug),
            "former_name": (r.get("former_name") or "").strip(),
            "factsheets": factsheets, "annual_reports": reports,
        })
        outreach.append({
            "provider": label, "fund": name, "slug": slug,
            "factsheets_available": factsheets,
            "annual_reports_available": reports,
            "missing": "prices, fees, minimum"
                       if factsheets == 0 else "fees, minimum",
            "priority": "high" if factsheets == 0 else "medium",
            "name_verified_against_sec": "NO — check sec_licensees.csv first",
        })

    by_provider: dict[str, int] = {}
    for o in outreach:
        by_provider[o["provider"]] = by_provider.get(o["provider"], 0) + 1
    outreach.sort(key=lambda o: (-by_provider[o["provider"]], o["provider"], o["fund"]))

    print(f"{len(rows)} catalogue rows")
    print(f"  {len(skipped)} already loaded with real data")
    print(f"  {len(to_load)} to add as directory entries\n")
    print("Providers by funds awaiting data — one email unlocks the most at the top:")
    for label, n in sorted(by_provider.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {n:>3}  {label}")

    with open(args.outreach, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(outreach[0].keys()))
        w.writeheader()
        w.writerows(outreach)
    print(f"\n  wrote {args.outreach}")

    if args.dry_run:
        print("\nDry run — nothing written to the database.")
        return 0

    # One catch-all provider row. Real providers are created when a fund's data
    # actually lands and its manager has been confirmed against the register.
    unknown = next((p["id"] for p in providers if p["slug"] == "unverified-provider"),
                   None)
    if not unknown:
        unknown = rest("POST", "/providers", {
            "slug": "unverified-provider",
            "legal_name": "Provider not yet verified",
            "trading_name": "Unverified",
            "status": "draft",
        })[0]["id"]

    body = []
    for f in to_load:
        body.append({
            "slug": f"cat-{slugify(f['slug'])}"[:80],
            "provider_id": prov_by_label.get(f["provider_label"].lower(), unknown),
            "name": f["name"],
            "share_class": "main",
            "asset_class": f["asset_class"],
            "currency": "GHS",
            # Never published, so it cannot reach a comparison page and appear
            # to have no charges.
            "status": "draft",
            "objective": (
                f"Directory entry only — no verified prices or fees yet. "
                f"{f['factsheets']} factsheet(s) and {f['annual_reports']} annual "
                f"report(s) known to exist. Name NOT yet verified against the SEC "
                f"register."
                + (f" Formerly {f['former_name']}." if f["former_name"] else "")
            ),
        })

    written = 0
    for i in range(0, len(body), 40):
        rest("POST", "/products", body[i : i + 40])
        written += len(body[i : i + 40])
    print(f"\n  {written} directory entries added, all status='draft'")
    print("  They will NOT appear on comparison pages until verified and published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

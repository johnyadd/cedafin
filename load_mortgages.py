"""
load_mortgages.py — the first Ghanaian mortgage figures, from the banks' own pages.

WHAT IS HERE AND WHY SO LITTLE
Two banks. Both read directly from their own sites on 13 September 2026.

Republic publishes four rates — but only on its mortgage calculator page. Its
Home Purchase product page says "Competitive Interest rates" and gives no
number, so a reader who goes to the product never sees one.

Absa publishes loan-to-value, tenor, debt service ratio, a maximum amount and
what insurance is included — and no rate at all.

Fidelity publishes no mortgage rate either. Three banks, three ways of not
saying, and that is the finding rather than an omission from this script.

THE CORRECTION THIS SCRIPT EXISTS BECAUSE OF
A search result served Republic's rates as 27% and 28%. Their live page says
18% and 23%. The search index was holding a cached copy of the same URL from
over a year earlier, and nothing on the result indicated it was stale.

Publishing the wrong one would have been a thirty-eight percent error on the
headline figure of a new section. The only defence is reading the page
yourself, which is what these figures are.

It is also an argument for snapshotting bank product pages the way we now
snapshot the SEC registers — the same address served different rates a year
apart, and only a kept copy proves when it changed.

WHAT IS DELIBERATELY NOT LOADED
Aggregator figures. Three sites gave three different sets of rates for these
banks — Absa at 22%, Stanbic at 21-24%, GCB at 15.9% — none sourced, none
agreeing. A number without a document behind it does not go on this site.

Usage:
    python load_mortgages.py --dry-run
    python load_mortgages.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-13"

REPUBLIC_CALC = "https://www.republicghana.com/products/mortgage/mortgage-calculate/"
REPUBLIC_HPM = "https://www.republicghana.com/products/mortgage/hpm/"
ABSA_HOME = "https://www.absa.com.gh/personal/get-a-home-loan/"


def env() -> dict:
    out = {}
    if os.path.exists(".env.local"):
        for line in open(".env.local", encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    for k in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    if not out.get("SUPABASE_SERVICE_ROLE_KEY"):
        print("Missing Supabase credentials — run from the project root.")
        sys.exit(1)
    return out


E = env()
BASE = E["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = E["SUPABASE_SERVICE_ROLE_KEY"]


def call(method: str, path: str, body=None, prefer: str | None = None):
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
    )
    req.add_header("apikey", KEY)
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("Content-Type", "application/json")
    if prefer:
        req.add_header("Prefer", prefer)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        print(f"\n  {e.code} on {method} {path}")
        print(f"  {e.read().decode('utf-8', 'replace')[:1500]}\n")
        raise


# Four products, one bank. Each is a distinct rate for a distinct borrower,
# which is more granularity than any other Ghanaian lender publishes.
REPUBLIC_PRODUCTS = [
    {
        "slug": "republic-mortgage-ghs-individual",
        "name": "Home Purchase Mortgage — individuals (GHS)",
        "rate": 0.18,
        "currency": "GHS",
        "lock_in_days": 7300,  # up to 20 years
        "note": "18% a year, fixed. Up to 20 years. Debt service ratio up to 50%.",
    },
    {
        "slug": "republic-mortgage-ghs-business",
        "name": "Home Purchase Mortgage — businesses (GHS)",
        "rate": 0.23,
        "currency": "GHS",
        "lock_in_days": 7300,
        "note": "23% a year, fixed, where the borrower is a business.",
    },
    {
        "slug": "republic-mortgage-usd",
        "name": "Home Purchase Mortgage (USD)",
        "rate": 0.115,
        "currency": "USD",
        "lock_in_days": 5475,  # up to 15 years
        "note": (
            "11.5% a year, fixed, up to 15 years. Up to 80% of value for "
            "non-residents. Debt service ratio up to 40%. The currency is the "
            "risk: a cedi earner servicing a dollar loan carries the exchange "
            "rate, and the cedi has moved a long way in both directions."
        ),
    },
    {
        "slug": "republic-mortgage-nhmf",
        "name": "National Home-Ownership Fund Mortgage Scheme",
        "rate": 0.135,
        "currency": "GHS",
        "lock_in_days": 7300,
        "note": (
            "13.5% a year under the government scheme — four and a half points "
            "below the same bank's standard individual rate. Eligibility is set "
            "by the scheme rather than the bank."
        ),
    },
]

REPUBLIC_ACCESS = (
    "Republic Bank state that their Home Purchase Mortgage is open to "
    "Resident and Non-Resident Ghanaians. They publish up to 100% of property "
    "value for resident Ghanaians borrowing in cedis, and up to 80% for "
    "non-residents borrowing in US dollars, with a minimum 20% equity "
    "contribution, a debt service ratio of 50% on cedi loans and 40% on dollar "
    "loans, and terms of up to 20 years in cedis or 15 years in dollars. Read "
    "from their own product page on 13 September 2026. The rate is not on that "
    "page — it appears only on their mortgage calculator."
)

ABSA_TERMS = (
    "Absa publish terms but no rate. Up to GHS 5,000,000; up to 90% finance "
    "for home purchase and construction in local currency and 80% in foreign "
    "currency; up to 70% for equity release or home improvement; maximum debt "
    "service ratio of 50% local and 45% foreign currency; tenor of 5 to 15 "
    "years for a fixed rate; property and credit life insurance covering "
    "death, permanent disability and retrenchment included. Read from their "
    "own page on 13 September 2026. No interest rate appears anywhere on it."
)


def source_for(url: str, title: str, publisher: str) -> str:
    have = call("GET", f"/sources?url=eq.{url}&select=id")
    if have:
        return have[0]["id"]
    return call(
        "POST",
        "/sources",
        {
            "kind": "manual_entry",
            "publisher": publisher,
            "title": title,
            "url": url,
            "retrieved_at": VERIFIED_ON,
        },
        prefer="return=representation",
    )[0]["id"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    republic = call(
        "GET", "/providers?slug=eq.republic-bank-ghana&select=id,trading_name"
    )
    absa = call("GET", "/providers?trading_name=ilike.*absa*&select=id,trading_name")

    if args.dry_run:
        print()
        print("  Republic Bank — four published mortgage rates")
        for p in REPUBLIC_PRODUCTS:
            print(f"    {p['rate'] * 100:>6.2f}%  {p['name']}")
        print()
        print("    All four from their mortgage calculator page. Their product")
        print("    page says 'Competitive Interest rates' and gives no number.")
        print()
        print("  Absa — terms published, no rate")
        print("    90% LTV local, 80% foreign, 70% equity release")
        print("    DSR 50% local, 45% foreign, tenor 5-15 years")
        print()
        print(f"  Provider records found: republic={bool(republic)} absa={bool(absa)}")
        print()
        print("  NOT loaded: aggregator figures. Three sites gave three")
        print("  different sets of rates for these banks, none sourced.")
        return 0

    if not republic:
        print("  republic-bank-ghana not found — check the provider slug.")
        return 1

    rid = republic[0]["id"]
    calc_src = source_for(
        REPUBLIC_CALC, "Republic Bank mortgage calculator — published rates", "Republic Bank (Ghana) PLC"
    )
    hpm_src = source_for(
        REPUBLIC_HPM, "Republic Bank Home Purchase Mortgage — product terms", "Republic Bank (Ghana) PLC"
    )

    made = 0
    for p in REPUBLIC_PRODUCTS:
        existing = call("GET", f"/products?slug=eq.{p['slug']}&select=id")
        body = {
            "slug": p["slug"],
            "name": p["name"],
            "provider_id": rid,
            "asset_class": "mortgage",
            "market_side": "borrow",
            "currency": p["currency"],
            "status": "published",
            # Both ends, because the schema requires a range and these are
            # fixed rates — min and max are the same number. That constraint
            # is right: a rate with one end open is not a rate.
            "rate_min": p["rate"],
            "rate_max": p["rate"],
            "lock_in_days": p["lock_in_days"],
            "eligibility_notes": p["note"],
            "min_source_id": calc_src,
            "min_verified_on": VERIFIED_ON,
        }
        if existing:
            call("PATCH", f"/products?id=eq.{existing[0]['id']}", body)
        else:
            call("POST", "/products", body)
        made += 1
        print(f"    {p['rate'] * 100:>6.2f}%  {p['name']}")

    call(
        "PATCH",
        f"/providers?id=eq.{rid}",
        {"access_requirements": REPUBLIC_ACCESS, "access_verified_on": VERIFIED_ON},
    )
    print(f"  Republic: {made} product(s), access terms recorded (source {hpm_src})")

    if absa:
        absa_src = source_for(
            ABSA_HOME, "Absa Bank Ghana home loan — published terms", "Absa Bank Ghana"
        )
        call(
            "PATCH",
            f"/providers?id=eq.{absa[0]['id']}",
            {"access_requirements": ABSA_TERMS, "access_verified_on": VERIFIED_ON},
        )
        print(f"  Absa: terms recorded, no rate published (source {absa_src})")
    else:
        print("  Absa provider record not found — terms not recorded")

    print()
    print("  Ghana now has published mortgage rates on this site for the first")
    print("  time. One bank of three publishes one, and only on a calculator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
load_ic_liquidity.py — the ninth Ghanaian fund with verified figures.

WHERE THIS CAME FROM
IC Securities replied to our question about brokerage costs by pointing at
their Help Centre, saying their fees are already published. The brokerage
commission is not there — the Tradelive section covers CSD setup, orders,
settlement and dividends, with no article on what a trade costs. But their
fund fee is, and it is more completely stated than most:

    "Yes, there is a yearly fee of up to 2% for managing the fund. This fee is
     taken little by little each day... There are no front-load or redemption
     fees."

That last sentence is the unusual part. Entry and exit charges are almost never
addressed by Ghanaian managers, and stating there are none is a disclosure the
others do not make.

WHY "UP TO 2%" IS STORED AS 2%
Their wording is a maximum, not a rate. We store 2.00% because it is the only
figure they give and it is the worst case a saver would pay, and the condition
records that it is a ceiling rather than a fixed charge. Storing a lower guess
would be inventing a number they did not publish.

WHY IT IS A SEPARATE PROVIDER FROM THE BROKERAGE
IC Securities (Ghana) Ltd is already recorded as a broker-dealer from the SEC
register. Fund management is a different licence and a different entity, so it
gets its own record rather than being folded into the brokerage — the same
separation the SEC register itself makes.

WHAT IS STILL MISSING
Minimum investment, dealing frequency, settlement period, and any return
history. Asked.

Usage:
    python load_ic_liquidity.py --dry-run
    python load_ic_liquidity.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

PROVIDER_SLUG = "ic-asset-managers"
FUND_SLUG = "ic-liquidity-fund"
SOURCE_URL = "https://wealth.ic.africa/help/"
VERIFIED_ON = "2026-09-03"

PROVIDER = {
    "slug": PROVIDER_SLUG,
    "legal_name": "IC Asset Managers (Ghana) Limited",
    "trading_name": "IC",
    "website": "https://wealth.ic.africa",
    "contact_email": "clientservice@ic.africa",
    "contact_phone": "+233 (0) 308 250 051 / +233 (0) 302 745 116",
    "office_address": "No. 2 Johnson Sirleaf Road, North Ridge, Accra",
    "status": "published",
    "notes": (
        "Publishes fund fees in a public Help Centre, including the absence of "
        "front-load and redemption charges — a disclosure no other Ghanaian "
        "manager we track makes. Brokerage commission for Tradelive is not "
        "published there; asked."
    ),
}


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
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        print(f"  provider  {PROVIDER['legal_name']}")
        print(f"  fund      IC Liquidity Fund (money market)")
        print(f"  charge    2.00% a year — their wording is 'up to 2%'")
        print(f"  no front-load, no redemption fee — stated explicitly")
        print(f"  source    {SOURCE_URL}, read {VERIFIED_ON}")
        print()
        print("  Minimum, dealing frequency and returns not published. Asked.")
        return 0

    # Source record, so the figure is citable on the page.
    src = call("GET", f"/sources?url=eq.{SOURCE_URL}&select=id")
    if src:
        source_id = src[0]["id"]
    else:
        made = call(
            "POST",
            "/sources",
            {
                # Columns are kind / publisher / title / url / retrieved_at —
                # the first attempt guessed retrieved_on and omitted kind.
                # kind is constrained to manual_entry, provider_factsheet or
                # regulator_publication. This was read off a web page, so
                # manual_entry is the honest one.
                "kind": "manual_entry",
                "url": SOURCE_URL,
                "title": "IC Wealth Help Centre — IC Liquidity Fund fees",
                "publisher": "IC Asset Managers",
                "retrieved_at": VERIFIED_ON,
            },
            prefer="return=representation",
        )
        source_id = made[0]["id"]
    print(f"  source {source_id}")

    existing = call("GET", f"/providers?slug=eq.{PROVIDER_SLUG}&select=id")
    if existing:
        pid = existing[0]["id"]
        call("PATCH", f"/providers?id=eq.{pid}", PROVIDER)
        print("  updated provider")
    else:
        made = call("POST", "/providers", PROVIDER, prefer="return=representation")
        pid = made[0]["id"]
        print("  created provider")

    prod = call("GET", f"/products?slug=eq.{FUND_SLUG}&select=id")
    if prod:
        product_id = prod[0]["id"]
        print("  fund exists")
    else:
        made = call(
            "POST",
            "/products",
            {
                "slug": FUND_SLUG,
                "name": "IC Liquidity Fund",
                "provider_id": pid,
                "asset_class": "money_market",
                "currency": "GHS",
                "market_side": "invest",
                "legal_structure": "mutual_fund",
                "status": "published",
            },
            prefer="return=representation",
        )
        product_id = made[0]["id"]
        print("  created fund")

    fees = [
        {
            "product_id": product_id,
            "fee_type": "management",
            "rate": 0.02,
            "basis": "annual_nav",
            "conditions": (
                "Their wording is 'up to 2%' — a ceiling, not a fixed rate. "
                "Accrued daily at 2%/365 on the fund value and already "
                "reflected in the quoted balance."
            ),
            "effective_from": VERIFIED_ON,
            "source_id": source_id,
            "verified_on": VERIFIED_ON,
        },
        {
            "product_id": product_id,
            "fee_type": "stated_charges",
            "rate": 0.02,
            "basis": "annual_nav",
            "conditions": (
                "The only charge published. IC state explicitly that there are "
                "no front-load and no redemption fees — a disclosure no other "
                "Ghanaian manager we track makes."
            ),
            "effective_from": VERIFIED_ON,
            "source_id": source_id,
            "verified_on": VERIFIED_ON,
        },
    ]
    for f in fees:
        have = call(
            "GET",
            f"/product_fees?product_id=eq.{product_id}&fee_type=eq.{f['fee_type']}&select=id",
        )
        if have:
            print(f"    fee exists: {f['fee_type']}")
            continue
        call("POST", "/product_fees", f)
        print(f"    added fee: {f['fee_type']} {f['rate']*100:.2f}%")

    print()
    print("  IC Liquidity Fund is live — the ninth Ghanaian fund with a")
    print("  verified charge, and the only one stating it has no entry or")
    print("  exit fees.")
    print()
    print("  Minimum, dealing frequency and return history still missing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

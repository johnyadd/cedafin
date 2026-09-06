"""
load_tbill4all.py — the lowest minimum in Ghana, and how you reach it.

WHAT THIS IS
Ecobank TBill4All: Government of Ghana 91-day and 182-day Treasury bills,
bought through an MTN Mobile Money wallet by dialling *770#. Minimum GH¢5.

WHY IT IS A SEPARATE PRODUCT AND NOT A MINIMUM ON THE EXISTING BILLS
The instrument is identical — the same government bill already on this site
under Government of Ghana. What differs is the way in, and from a saver's
point of view that is the whole decision: GH¢5 through a phone with no bank
account is not the same offering as several hundred cedis through a branch.

Recording GH¢5 against the bills generally would say Treasury bills cost GH¢5
to buy, which is untrue at a bank counter. So it is listed separately, with a
note saying plainly that the underlying instrument is the same one.

The site already handles gold this way: the Ghana Gold Coin and the NewGold
ETF are both claims on gold and both listed, because the cost and the access
differ.

WHY IT CORRECTS SOMETHING WE PUBLISHED
Our guide says GH₵20 at Stanbic Cash Trust is the lowest verified minimum in
Ghana. This is four times lower, and it is a government bill rather than a
fund. The guide needs amending once this loads.

ACCESS REQUIREMENTS, AND WHAT WE WILL NOT DO
The access field records what the provider STATES is needed. Ecobank say a
one-time registration on *770# and an MTN Mobile Money wallet, with no bank
account required.

What we do not record is whether a non-resident can use it. An MTN Ghana
wallet is plainly needed and a diaspora investor plainly may struggle to hold
one — but "plainly" is inference, and inference presented as fact is the
error this site exists to point out. The requirement is recorded; the reader
draws the conclusion.

Usage:
    python load_tbill4all.py --dry-run
    python load_tbill4all.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

PROVIDER_SLUG = "ecobank-capital-advisors"
PRODUCT_SLUG = "ecobank-tbill4all"
VERIFIED_ON = "2026-09-05"

PRODUCT_URL = (
    "https://ecobank.com/gh/personal-banking/products-services/"
    "investment-solutions/tbill4all"
)

PROVIDER = {
    "slug": PROVIDER_SLUG,
    "legal_name": "Ecobank Capital Advisors Limited",
    "trading_name": "Ecobank Capital Advisors",
    "website": PRODUCT_URL,
    "contact_phone": "3225 (free) / +233 302 213 999",
    "status": "published",
    "notes": (
        "A wholly-owned subsidiary of Ecobank. Distributes Government of Ghana "
        "Treasury bills through MTN Mobile Money as TBill4All — the lowest "
        "published minimum of any investment product we track."
    ),
}

# Ecobank's own wording, condensed. Every clause is something they state.
ACCESS = (
    "One-time registration by dialling *770# from an MTN Mobile Money wallet. "
    "Ecobank state that no bank account is required. Purchases, rediscounting "
    "and statements are all done from the phone; confirmation arrives by text. "
    "Ecobank also state that no taxes are payable on Treasury bills bought "
    "through the platform."
)

PRODUCT = {
    "slug": PRODUCT_SLUG,
    "name": "Treasury bills via Ecobank TBill4All",
    "asset_class": "government_security",
    "currency": "GHS",
    "market_side": "invest",
    "status": "published",
    "min_initial_minor": 500,  # GH¢5.00 in pesewas
    "min_verified_on": VERIFIED_ON,
    # Ecobank state this on their own FAQ, so it belongs in the tax fields
    # rather than buried in the access note.
    "tax_exempt": True,
    "tax_note": (
        "Ecobank state that no taxes are payable on Treasury bills purchased "
        "through the TBill4All platform."
    ),
    "tax_verified_on": VERIFIED_ON,
    "dealing_frequency": "on_application",
    # channels is an array column, not free text.
    "channels": ["mobile_money"],
    "access_requirements": ACCESS,
    "access_verified_on": VERIFIED_ON,
    "eligibility_notes": (
        "The same 91-day and 182-day Government of Ghana Treasury bills listed "
        "elsewhere on this site — this is a distribution channel, not a "
        "different instrument. What differs is the minimum and the way in."
    ),
}

SOURCE = {
    "kind": "manual_entry",
    "publisher": "Ecobank Ghana",
    "title": "Ecobank TBILL4ALL — product page and FAQs",
    "url": PRODUCT_URL,
    "retrieved_at": VERIFIED_ON,
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
        print(f"  product   {PRODUCT['name']}")
        print(f"  minimum   GH¢{PRODUCT['min_initial_minor']/100:.2f}")
        print(f"  source    {PRODUCT_URL}")
        print()
        print("  Access requirements recorded:")
        for line in ACCESS.split(". "):
            if line.strip():
                print(f"    - {line.strip().rstrip('.')}.")
        print()
        print("  Against what the site currently says is the lowest minimum:")
        print("    Stanbic Cash Trust   GH¢20.00")
        print("    TBill4All            GH¢ 5.00   <- four times lower")
        print()
        print("  The guide will need amending once this loads.")
        return 0

    src = call("GET", f"/sources?url=eq.{PRODUCT_URL}&select=id")
    source_id = (
        src[0]["id"]
        if src
        else call("POST", "/sources", SOURCE, prefer="return=representation")[0]["id"]
    )
    print(f"  source {source_id}")

    existing = call("GET", f"/providers?slug=eq.{PROVIDER_SLUG}&select=id")
    if existing:
        pid = existing[0]["id"]
        call("PATCH", f"/providers?id=eq.{pid}", PROVIDER)
        print("  updated provider")
    else:
        pid = call("POST", "/providers", PROVIDER, prefer="return=representation")[0][
            "id"
        ]
        print("  created provider")

    body = {**PRODUCT, "provider_id": pid}
    have = call("GET", f"/products?slug=eq.{PRODUCT_SLUG}&select=id")
    if have:
        call("PATCH", f"/products?id=eq.{PRODUCT_SLUG and have[0]['id']}", body)
        print("  updated product")
    else:
        call("POST", "/products", body)
        print("  created product")

    print()
    print("  GH¢5 is now the lowest minimum on the site, by a factor of four.")
    print()
    print("  Two things follow:")
    print("    - the guide says GH₵20 is the floor; it is not")
    print("    - the access field is populated for one product out of ~80")
    return 0


if __name__ == "__main__":
    sys.exit(main())

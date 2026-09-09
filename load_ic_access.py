"""
load_ic_access.py — the first complete published route.

WHAT MAKES THIS DIFFERENT FROM THE OTHER FIVE
Every entry on the diaspora page so far answers part of the question. Ecobank
tells you the minimum but needs an MTN Ghana wallet. Databank tells you a
foreign national is accepted, at twenty thousand dollars. SBG tells you to
email the form.

IC publishes the whole journey, in their own FAQ:

    "To invest, first open an account with IC at onboarding.ic.africa. You will
     need a passport-sized picture and a valid national ID (Passport,
     Ghana/Ecowas ID Card). Your account will be activated within 24 hours and
     then you can invest in the fund by going to wealth.ic.africa where you can
     pay using your debit/credit card or mobile wallet, or also set up a direct
     debit instruction from your bank."

And the way out:

    "Simply log into your wealth.ic.africa account and select 'withdraw'. Your
     cash will be paid to your bank or mobile wallet details that are
     associated with your IC account."

Onboarding, identification, activation time, funding and withdrawal — the five
things our seven questions ask about, published without being asked.

THE DETAIL THAT MATTERS MOST
Passport is named as acceptable identification. A Ghanaian in London has a
passport and may well not have a Ghana Card, so an ID requirement that names
only the Ghana Card would exclude them. This one does not.

WHAT IT STILL DOES NOT SAY
Whether IC accepts an applicant who is RESIDENT outside Ghana. The FAQ says
what documents are needed, not who may apply. A satisfiable document
requirement is not an eligibility statement, and we should not present it as
one — the same distinction we drew for Databank's form.

AND IT CORRECTS SOMETHING WE PUBLISH
The minimum to open and maintain an IC Liquidity Fund account is GHS 1.00.
Our guide says Ecobank's GH¢5 is the lowest minimum in Ghana. It is five times
that.

Usage:
    python load_ic_access.py --dry-run
    python load_ic_access.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-09"
FUND_SLUG = "ic-liquidity-fund"
PROVIDER_SLUG = "ic-asset-managers"
SOURCE_URL = "https://www.ic.africa/ic-liquidity/"

ACCESS = (
    "IC publish the whole route. Their FAQ states that you open an account at "
    "onboarding.ic.africa with a passport-sized picture and a valid national "
    "ID — and names Passport or a Ghana/Ecowas ID card as acceptable. The "
    "account is activated within 24 hours, after which you invest at "
    "wealth.ic.africa paying by debit or credit card, mobile wallet, bank "
    "transfer, bank deposit or ExpressPay, or by setting up a direct debit. "
    "To take money out you log in and select withdraw, and the cash is paid to "
    "the bank or mobile wallet associated with your IC account. Read from "
    "their own material on 9 September 2026. What the FAQ does not say is "
    "whether somebody resident outside Ghana may apply — it states which "
    "documents are accepted, not who is eligible. A passport being acceptable "
    "means the requirement is satisfiable from abroad; it does not mean the "
    "application would be. We have asked."
)


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
        print(f"  {e.read().decode('utf-8', 'replace')[:400]}\n")
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        print("  IC Liquidity Fund")
        print()
        print("    minimum   GH¢1.00 — published, and five times lower than")
        print("              Ecobank's GH¢5 which our guide calls the lowest")
        print("              in Ghana")
        print("    ID        passport OR Ghana/Ecowas card — a passport being")
        print("              acceptable is what makes this reachable from abroad")
        print("    activation within 24 hours")
        print("    funding   card, mobile wallet, transfer, deposit, ExpressPay,")
        print("              direct debit")
        print("    withdrawal online, to the bank or wallet on the account")
        print()
        print("  Five of the seven questions our page tells readers to ask,")
        print("  answered without being asked. No other Ghanaian provider we")
        print("  have checked does that.")
        print()
        print("  NOT established: whether a non-resident may apply. The FAQ")
        print("  says which documents are accepted, not who is eligible.")
        return 0

    src = call("GET", f"/sources?url=eq.{SOURCE_URL}&select=id")
    if src:
        source_id = src[0]["id"]
    else:
        source_id = call(
            "POST",
            "/sources",
            {
                "kind": "manual_entry",
                "publisher": "IC Asset Managers",
                "title": "IC Liquidity Fund — frequently asked questions",
                "url": SOURCE_URL,
                "retrieved_at": VERIFIED_ON,
            },
            prefer="return=representation",
        )[0]["id"]
    print(f"  source {source_id}")

    have = call("GET", f"/products?slug=eq.{FUND_SLUG}&select=id")
    if not have:
        print(f"  {FUND_SLUG} not found — run load_ic_liquidity.py first.")
        return 1

    call(
        "PATCH",
        f"/products?id=eq.{have[0]['id']}",
        {
            "access_requirements": ACCESS,
            "access_verified_on": VERIFIED_ON,
            # GH¢1.00 in pesewas. Published, and lower than anything else we
            # hold — including the GH¢5 our guide calls the lowest in Ghana.
            "min_initial_minor": 100,
            "min_verified_on": VERIFIED_ON,
            "min_source_id": source_id,
            "dealing_frequency": "daily",
            "eligibility_notes": (
                "Minimum GH¢1 to open and maintain. IC publish the full "
                "route — onboarding, identification, activation time, funding "
                "and withdrawal — which no other Ghanaian provider we track "
                "does."
            ),
        },
    )
    print("  updated IC Liquidity Fund")
    print()
    print("  GH¢1 is now the lowest published minimum on the site. The guide")
    print("  still says GH¢5, and needs correcting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

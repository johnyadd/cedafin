"""
load_fnb_mortgage.py — the mortgage bank, and a correction it forces.

WHO THEY ARE
First National Bank Ghana acquired Ghana Home Loans, the former GHL Bank, and
the Ghanaian business press describes them as the country's mortgage leaders.
If any bank in Ghana was going to publish a rate, it was this one.

They do not. Twenty-one banks scanned; Republic remains the only one.

WHAT THEY DO PUBLISH, AND WHY IT BELONGS ON THE DIASPORA PAGE
Four home loan products, each stated as available to resident AND non-resident
Ghanaians, each in GHS, USD or GBP, each up to twenty years:

  First-Time Buyer     — needs an offer letter from the vendor to qualify
  Buy to Let           — for borrowers who already own a residential property
  Home Construction    — a one-year construction facility rolled into a
                         long-term loan
  100% Purchase        — for a first-time buyer who cannot raise the deposit,
                         with an additional insurance policy of up to 30% of
                         the purchase price

That last one is worth reading carefully. The 30% is INSURANCE, not a
loan-to-value ratio and not a deposit. An automated scan matched it as an LTV
and it took reading the page to see otherwise.

THE CORRECTION THIS FORCES
Stanbic's entry on this site said sterling and euro mortgages were offered
"at no other Ghanaian lender". First National offer GBP across all four
products, and have done for years. The claim was wrong when written and is
removed here.

It was wrong because we had checked four banks and generalised to
twenty-three. The scanner that found First National exists because of that
kind of mistake.

Usage:
    python load_fnb_mortgage.py --dry-run
    python load_fnb_mortgage.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-14"
PAGE = "https://www.firstnationalbank.com.gh/loans/homeLoan.html"

FNB_TERMS = (
    "First National publish four home loan products and state for each that "
    "it is available to resident and non-resident Ghanaians, with funds in "
    "cedis, US dollars or pounds sterling and up to twenty years to repay.\n\n"
    "The First-Time Buyer Home Loan requires an offer letter from the vendor "
    "to qualify. The Buy to Let Home Loan is for borrowers who already own a "
    "residential property and want another to rent out. The Home Construction "
    "Home Loan is a two-part facility — a one-year construction loan rolled "
    "into a long-term mortgage. And the 100% Purchase Home Loan is for a "
    "first-time buyer unable to raise the minimum deposit, carrying an "
    "additional insurance policy of up to 30% of the purchase price.\n\n"
    "That 30% is insurance rather than a deposit or a loan-to-value ratio, "
    "and is easy to misread as either.\n\n"
    "First National acquired Ghana Home Loans, the former GHL Bank, and are "
    "described in the Ghanaian business press as the country's mortgage "
    "leaders. They publish no interest rate on any of the four products.\n\n"
    "Read from their own material on 14 September 2026."
)

# The claim being removed, and what replaces it.
STANBIC_WRONG = (
    " And sterling and euro are offered, which we have found at no other "
    "Ghanaian lender: somebody earning in those currencies can borrow in "
    "them, and so carries no exchange rate risk on the repayments."
)
STANBIC_RIGHT = (
    " And sterling and euro are offered, so somebody earning in those "
    "currencies can borrow in them and carries no exchange rate risk on the "
    "repayments. First National Bank offer cedis, dollars or pounds across "
    "four home loan products; we said at first that no other Ghanaian lender "
    "offered this, which was wrong — we had checked four banks and "
    "generalised to twenty-three."
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
        print(f"  {e.read().decode('utf-8', 'replace')[:600]}\n")
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fnb = call(
        "GET",
        "/providers?trading_name=ilike.*First%20National*&select=id,slug,access_requirements",
    )
    stanbic = call(
        "GET",
        "/providers?slug=eq.stanbic-bank-ghana&select=id,access_requirements",
    )

    if args.dry_run:
        print()
        print("  First National Bank (Ghana) — four home loan products")
        print()
        print("    All four: resident AND non-resident Ghanaians")
        print("    All four: GHS, USD or GBP, up to 20 years")
        print("    First-Time Buyer, Buy to Let, Home Construction,")
        print("    and 100% Purchase for buyers without a deposit")
        print()
        print("    No rate published. Republic remains the only one.")
        print()
        print("  CORRECTION to Stanbic's entry:")
        print("    said sterling and euro were offered at no other lender.")
        print("    First National offer GBP. Claim removed.")
        print()
        print(f"  FNB record: {bool(fnb)}   Stanbic record: {bool(stanbic)}")
        if stanbic and STANBIC_WRONG in (stanbic[0].get("access_requirements") or ""):
            print("  The wrong sentence was found and will be replaced.")
        else:
            print("  WARNING: could not find the exact sentence to replace.")
        return 0

    if not fnb:
        print("  First National provider record not found.")
        return 1

    have = call("GET", f"/sources?url=eq.{PAGE}&select=id")
    src = (
        have[0]["id"]
        if have
        else call(
            "POST",
            "/sources",
            {
                "kind": "manual_entry",
                "publisher": "First National Bank (Ghana)",
                "title": "First National Bank Ghana home loans — published terms",
                "url": PAGE,
                "retrieved_at": VERIFIED_ON,
            },
            prefer="return=representation",
        )[0]["id"]
    )

    call(
        "PATCH",
        f"/providers?id=eq.{fnb[0]['id']}",
        {"access_requirements": FNB_TERMS, "access_verified_on": VERIFIED_ON},
    )
    print(f"  First National terms recorded (source {src})")

    call(
        "POST",
        "/provider_disclosure?on_conflict=provider_id,field",
        [
            {
                "provider_id": fnb[0]["id"],
                "field": "non_resident_access",
                "published_on": VERIFIED_ON,
                "checked_on": VERIFIED_ON,
                "asked_on": None,
                "answered_on": None,
                "source_kind": "provider_site",
                "note": None,
            }
        ],
        prefer="resolution=merge-duplicates",
    )
    print("  Non-resident access recorded as published")

    if stanbic:
        current = stanbic[0].get("access_requirements") or ""
        if STANBIC_WRONG in current:
            call(
                "PATCH",
                f"/providers?id=eq.{stanbic[0]['id']}",
                {"access_requirements": current.replace(STANBIC_WRONG, STANBIC_RIGHT)},
            )
            print("  Stanbic claim corrected")
        else:
            print("  Stanbic sentence not found — correct it by hand")

    print()
    print("  Twenty-one banks scanned for a published mortgage rate.")
    print("  One has it. The bank that leads the market does not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
load_stanbic_mortgage.py — terms, four currencies, and no rate.

THE PATTERN, NOW ON ITS FOURTH INSTITUTION
  Republic  — four rates, published only on a calculator
  Absa      — LTV, tenor, DSR, maximum, insurance. No rate.
  Fidelity  — "competitive interest rates on borrowings". No rate.
  Stanbic   — seven products, LTV, four currencies. No rate.
  NorthStar — the only licensed mortgage specialist. No rate.

One bank of five publishes a number, and puts it where somebody reading about
the mortgage will not see it.

WHAT IS NEW IN STANBIC'S DISCLOSURE, AND WORTH THE LOAD

  The rate is VARIABLE. Republic's four are fixed. Nobody else on this site
  records the distinction, and it is the difference between knowing what a
  twenty-year loan costs and not.

  Four currencies: GHS, USD, GBP and EUR.

That second one matters more than it looks. A Ghanaian earning sterling in
London borrowing in sterling carries no currency risk; the same person
borrowing Republic's dollars against cedi rent carries a great deal. We have
found no other Ghanaian lender publishing a sterling or euro mortgage, which
makes it a diaspora finding as much as a lending one.

Usage:
    python load_stanbic_mortgage.py --dry-run
    python load_stanbic_mortgage.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-13"
STANBIC_HOME = (
    "https://www.stanbicbank.com.gh/gh/personal/products-and-services/"
    "borrow-for-your-needs/home-loans"
)

TERMS = (
    "Stanbic publish seven home loan products and no rate. Home Purchase at "
    "up to 80% financing; Developer Construction, where the bank pays the "
    "developer in stages; Refinancing, internal, external or cash-out; Equity "
    "Release against an existing property; Home Improvement; an Employer "
    "Group Mortgage Scheme; and Vacant Land Financing at up to 60%. They "
    "state no maximum loan amount, describing it as dependent on income.\n\n"
    "The rate is described only as a competitive variable interest rate in "
    "GHS, USD, GBP or EUR. Two things follow. It is variable, where Republic "
    "Bank's published mortgage rates are fixed — which is the difference "
    "between knowing what a twenty-year loan costs and not. And sterling and "
    "euro are offered, which we have found at no other Ghanaian lender: "
    "somebody earning in those currencies can borrow in them, and so carries "
    "no exchange rate risk on the repayments."
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

    prov = call(
        "GET",
        "/providers?slug=eq.stanbic-bank-ghana&select=id,trading_name",
    )

    if args.dry_run:
        print()
        print("  Stanbic Bank Ghana — home loans")
        print()
        print("    Seven products. Home Purchase 80% LTV, Vacant Land 60%.")
        print("    No maximum, dependent on income.")
        print("    Rate: VARIABLE, in GHS, USD, GBP or EUR. No number.")
        print()
        print("    New here: the variable/fixed distinction, and sterling and")
        print("    euro lending — which we have found nowhere else in Ghana.")
        print()
        print(f"  Provider record found: {bool(prov)}")
        print()
        print("  Five institutions checked. One publishes a rate.")
        return 0

    if not prov:
        print("  stanbic-bank-ghana not found — check the provider slug.")
        return 1

    src = source_for(
        STANBIC_HOME, "Stanbic Bank Ghana home loans — published terms", "Stanbic Bank Ghana"
    )
    call(
        "PATCH",
        f"/providers?id=eq.{prov[0]['id']}",
        {"access_requirements": TERMS, "access_verified_on": VERIFIED_ON},
    )
    print(f"  Stanbic terms recorded (source {src})")

    # No provider_disclosure write here, deliberately.
    #
    # This used to record "no published mortgage rate" into the lending_rate
    # field with merge-duplicates. But Stanbic files Bank of Ghana's lending
    # return, so its lending_rate record was already "published" — and this
    # silently overwrote it. The disclosure page then listed Stanbic among
    # banks that publish nothing. A narrow fact must not be written into a
    # broad field another writer owns; see ARCHITECTURE.md section 5.

    print()
    print("  Stanbic joins the diaspora page: sterling and euro mortgages let")
    print("  somebody earning abroad borrow in the currency they are paid in.")
    print("  First National offers pounds too; this is no longer the only one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

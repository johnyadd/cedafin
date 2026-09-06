"""
load_databank_access.py — the first published answer to the question.

WHAT THIS RECORDS
Databank's own documents state more about non-resident access than any other
Ghanaian provider we have checked. Three things, all in their words:

  Wealth Management — "Can a foreign national open an investment account with
  Wealth Management? Yes. However we would require a scanned copy of an
  international ID and deposit made via bank transfer."

  The same page states the minimum: the cedi equivalent of USD 20,000.

  Brokerage account opening — their form carries explicit non-resident fields:
  foreign residential address, foreign mailing address, foreign telephone,
  foreign tax identification number, and "Proof of Foreign Address (for
  Non-Resident clients)" among required documents.

  MFund — "You can open an account at any Databank location, online or via our
  USSD code *6100#." Residency is not addressed either way.

WHY THE MINIMUM MATTERS MORE THAN THE YES
Research handed to us presented Wealth Management as the strongest diaspora
evidence in the Ghanaian market. It is — and it is for people with twenty
thousand dollars. Recording the "yes" without the minimum would have told
ordinary savers abroad that a door was open which is not open to them.

So the minimum goes in the access note itself, not in a footnote.

WHY THE BROKERAGE FORM IS THE BETTER FINDING
It provides for non-residents without stating a floor, and it is for share
dealing — the thing our brokers page says nobody publishes access terms for.
A form with a field for a foreign tax identification number was designed to be
completed by somebody abroad.

WHAT THIS DOES NOT SAY
That a non-resident will be accepted. A form providing for something is not a
policy statement, and Databank have not answered our email. The requirement is
recorded; the conclusion is not drawn.

Usage:
    python load_databank_access.py --dry-run
    python load_databank_access.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

VERIFIED_ON = "2026-09-05"

WEALTH_URL = "https://www.databankgroup.com/databank-wealth-management/"
MFUND_URL = "https://www.databankgroup.com/mfund/"
FORM_URL = (
    "https://www.databankgroup.com/wp-content/uploads/2024/09/"
    "Account-opening-form_SEC-NEW_Brokerage-Jan-2024.pdf"
)

PROVIDER = {
    "slug": "databank",
    "legal_name": "Databank Financial Services Limited",
    "trading_name": "Databank",
    "website": "https://www.databankgroup.com",
    "contact_email": "info@databankgroup.com",
    "status": "published",
    "notes": (
        "States more about non-resident access than any other Ghanaian "
        "provider we have checked — foreign nationals accepted for Wealth "
        "Management at a USD 20,000 minimum, and a brokerage account form "
        "carrying explicit non-resident fields. Asked to confirm what applies "
        "to their funds."
    ),
}

# One entry per product, each quoting or closely paraphrasing Databank.
PRODUCTS = [
    {
        "slug": "databank-wealth-management",
        "name": "Databank Wealth Management",
        "asset_class": "balanced",
        "min_initial_minor": None,  # USD, not cedis — stated in the note
        "access": (
            "Databank state that a foreign national can open a Wealth "
            "Management account, requiring a scanned copy of an international "
            "ID and a deposit made by bank transfer. The same page states a "
            "minimum of the cedi equivalent of USD 20,000. Documents listed: "
            "completed mandate form and questionnaire, passport photograph, "
            "national ID or passport, proof of address, and a client "
            "indemnity form."
        ),
        "source": WEALTH_URL,
        "eligibility": (
            "Discretionary management rather than a single fund. The USD "
            "20,000 minimum is Databank's, published on the same page as the "
            "statement that foreign nationals are accepted."
        ),
    },
    {
        "slug": "databank-mfund",
        "name": "Databank MFund",
        "asset_class": "money_market",
        "min_initial_minor": None,
        "access": (
            "Databank state that an account can be opened at any Databank "
            "location, online, or by USSD on *6100#. Whether a non-resident "
            "can complete the online route is not addressed either way."
        ),
        "source": MFUND_URL,
        "eligibility": (
            "Ghana's first money market fund, launched 2004. Charges and "
            "minimum not yet obtained — asked."
        ),
    },
]

# Recorded against the provider rather than a product, since it governs share
# dealing generally rather than one instrument.
BROKERAGE_NOTE = (
    "Databank's brokerage account opening form carries explicit non-resident "
    "provisions: fields for foreign residential address, foreign mailing "
    "address, foreign telephone and foreign tax identification number, and "
    "\"Proof of Foreign Address (for Non-Resident clients)\" among the "
    "required documents. A form providing for something is not a policy "
    "statement, and we have asked Databank to confirm what they accept."
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


def source_for(url: str, title: str) -> str:
    have = call("GET", f"/sources?url=eq.{url}&select=id")
    if have:
        return have[0]["id"]
    made = call(
        "POST",
        "/sources",
        {
            "kind": "manual_entry",
            "publisher": "Databank",
            "title": title,
            "url": url,
            "retrieved_at": VERIFIED_ON,
        },
        prefer="return=representation",
    )
    return made[0]["id"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        print(f"  provider  {PROVIDER['legal_name']}")
        print()
        for p in PRODUCTS:
            print(f"  {p['name']}")
            print(f"    {p['access'][:150]}...")
            print()
        print("  Provider-level note on brokerage:")
        print(f"    {BROKERAGE_NOTE[:150]}...")
        print()
        print("  The USD 20,000 minimum is in the access note deliberately.")
        print("  Research handed to us called Wealth Management the strongest")
        print("  diaspora evidence in Ghana without mentioning it.")
        return 0

    existing = call("GET", "/providers?slug=eq.databank&select=id")
    body = {**PROVIDER, "notes": PROVIDER["notes"] + " " + BROKERAGE_NOTE}
    if existing:
        pid = existing[0]["id"]
        call("PATCH", f"/providers?id=eq.{pid}", body)
        print("  updated provider")
    else:
        pid = call("POST", "/providers", body, prefer="return=representation")[0]["id"]
        print("  created provider")

    for p in PRODUCTS:
        src = source_for(p["source"], f"Databank — {p['name']}")
        row = {
            "slug": p["slug"],
            "name": p["name"],
            "provider_id": pid,
            "asset_class": p["asset_class"],
            "currency": "GHS",
            "market_side": "invest",
            "legal_structure": "mutual_fund",
            "access_requirements": p["access"],
            "access_verified_on": VERIFIED_ON,
            "eligibility_notes": p["eligibility"],
            # Draft: no charge, no minimum, no return means nothing to compare
            # on. The access note is the point of the record.
            "status": "draft",
        }
        have = call("GET", f"/products?slug=eq.{p['slug']}&select=id")
        if have:
            call("PATCH", f"/products?id=eq.{have[0]['id']}", row)
            print(f"    updated {p['name']}")
        else:
            call("POST", "/products", row)
            print(f"    created {p['name']}")

    print()
    print("  Databank is the first Ghanaian provider on this site with a")
    print("  published position on non-resident access — and the position is")
    print("  'yes, at twenty thousand dollars', which is worth stating plainly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

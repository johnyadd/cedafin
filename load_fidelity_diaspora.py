"""
load_fidelity_diaspora.py — the third bank, and the cheapest to open.

WHERE IT SITS AGAINST THE OTHER TWO
  Absa    — no minimum balance, but certification of documents by a lawyer,
            notary or court is mandatory for Ghanaians living abroad.
  Zenith  — GHS 500 initial and GHS 200 maintained, an emailed copy of a
            Ghana Card or passport, and a cedi account before any foreign
            currency one.
  Fidelity — 100 units in any of GHS, USD, GBP or EUR, no cedi account first,
            zero maintenance fees, and 2% a year on the cedi balance.

On the published terms Fidelity is the cheapest of the three to open and the
only one paying interest. That is the comparison, and no bank could make it,
because none of them knows what the others require.

THE TWO CONSTRAINTS WORTH PUBLISHING ALONGSIDE
Their account opening form states identification as "ONLY Valid National
I.D", which is narrower than the passport-or-Ghana-Card the others accept,
and that to open with cash the customer must deposit at the nearest branch.
Neither is fatal from abroad but both are the kind of thing somebody should
know before starting.

AND THE ONE THAT COSTS MONEY
Their mortgage application form requires a Power of Attorney where the
applicant is non-resident. That is a legal instrument, drawn by a lawyer, and
nobody else on this site mentions it. It belongs beside the Absa
certification requirement and the EDC notarisation one: three providers, three
different pieces of paper that must be obtained abroad, none stating a cost.

Usage:
    python load_fidelity_diaspora.py --dry-run
    python load_fidelity_diaspora.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-14"
PAGE = "https://fidelitybank.com.gh/retail/borrow/"
FORM = "https://www.fidelitybank.com.gh/downloadables/forms/29-nrg-account/file"

TERMS = (
    "Fidelity publish a Non-Resident Ghanaian Account, marketed as Bank Home "
    "From Abroad and described as designed for Ghanaians abroad, giving a way "
    "to manage finances and bank securely from anywhere in the world.\n\n"
    "The terms are the most generous of any Ghanaian bank we have found. "
    "Minimum opening and operating balance is 100 — in cedis, dollars, pounds "
    "or euros, with no requirement to hold a cedi account first. There is no "
    "monthly maintenance fee on any currency. The cedi account pays 2% a year, "
    "credited monthly on balances of GHS 5,000 and above. It carries a "
    "chequebook, a Visa debit card and access to the mobile app and ATMs — and "
    "access to a mortgage facility worth up to US$500,000.\n\n"
    "Two constraints sit in their account opening form. Identification is "
    "stated as \"ONLY Valid National I.D\", which is narrower than the "
    "passport-or-Ghana-Card other banks accept. And to open the account with "
    "cash, the form says the customer must deposit it at the nearest branch. "
    "Requirements otherwise are a completed and endorsed form, two "
    "passport-sized photographs, confirmation of residential address and an "
    "initial deposit.\n\n"
    "One further requirement is worth knowing before applying for the "
    "mortgage rather than after: their mortgage application form requires a "
    "Power of Attorney where the applicant is non-resident. That is a legal "
    "instrument drawn by a lawyer, and no other Ghanaian provider we track "
    "mentions needing one.\n\n"
    "Read from their own material on 14 September 2026. No mortgage interest "
    "rate is published anywhere on their site."
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


def source_for(url: str, title: str) -> str:
    have = call("GET", f"/sources?url=eq.{url}&select=id")
    if have:
        return have[0]["id"]
    return call(
        "POST",
        "/sources",
        {
            "kind": "manual_entry",
            "publisher": "Fidelity Bank Ghana",
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
        "/providers?trading_name=ilike.*fidelity*&select=id,slug,trading_name",
    )

    if args.dry_run:
        print()
        print("  Fidelity Bank Ghana — Non-Resident Ghanaian Account")
        print()
        print("    100 in GHS, USD, GBP or EUR. No cedi account first.")
        print("    Zero maintenance fees. 2% a year on the cedi balance.")
        print("    Mortgage access up to US$500,000.")
        print()
        print("    Constraints: 'ONLY Valid National I.D'; cash opening needs")
        print("    a branch visit; mortgage needs a Power of Attorney if")
        print("    non-resident.")
        print()
        print("  Against the other two:")
        print("    Absa   — no minimum, mandatory certification")
        print("    Zenith — GHS 500, emailed passport copy, cedi account first")
        print("    Fidelity — 100 any currency, 2% interest, no fees")
        print()
        for p in prov or []:
            print(f"  Provider: {p['slug']} ({p['trading_name']})")
        return 0

    if not prov:
        print("  No Fidelity provider record found.")
        return 1

    src = source_for(PAGE, "Fidelity Bank Ghana — Bank Home From Abroad terms")
    source_for(FORM, "Fidelity Bank Ghana — Non-Resident Ghanaian account opening form")

    call(
        "PATCH",
        f"/providers?id=eq.{prov[0]['id']}",
        {"access_requirements": TERMS, "access_verified_on": VERIFIED_ON},
    )
    print(f"  Fidelity diaspora terms recorded (source {src})")

    call(
        "POST",
        "/provider_disclosure?on_conflict=provider_id,field",
        [
            {
                "provider_id": prov[0]["id"],
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

    print()
    print("  Three banks now state a diaspora position, and they differ enough")
    print("  that the cheapest depends on what the applicant already has: a")
    print("  notary, GHS 500, or neither.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

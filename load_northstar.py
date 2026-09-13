"""
load_northstar.py — the whole of a regulatory category, in one provider.

WHAT THIS IS
Bank of Ghana maintains a register of licensed Mortgage Finance institutions.
It has one entry: NorthStar Home Finance Company Limited.

Not one of several. One. A category of financial institution exists in
Ghanaian law and a single company occupies it.

WHY IT MATTERS TO THE MORTGAGE WORK
We had been checking banks, because that is where mortgages appeared to live.
The specialist register was not something anybody had looked at — including
us, until the SEC snapshot work led to Bank of Ghana's own registers.

And the answer is the same as the banks': NorthStar publishes what they do
(residential purchase, home improvement, home equity release, project
financing) and nothing about what it costs. No rate, no minimum, no
loan-to-value, no term.

SO THE FINDING IS NOW COMPLETE ACROSS THE CATEGORY
  Republic — four rates, published only on a calculator
  Absa — terms published, no rate
  Fidelity — no rate
  GCB — no mortgage product at all
  NorthStar — the only licensed specialist, no rate

Nobody in Ghana tells a borrower what a mortgage costs before contact. That is
a stronger claim than "banks are cagey", and it is now checkable.

WHAT IS NOT LOADED
Any rate. Third-party sources put Ghanaian mortgage rates at 25-35%, which
contradicts Republic's published 18% and comes from nobody's own document.

Usage:
    python load_northstar.py --dry-run
    python load_northstar.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-13"

REGISTER_URL = (
    "https://www.bog.gov.gh/supervision-regulation/"
    "registered-institutions/mortgage-finance/"
)
SITE_URL = "https://northstarhomefinance.com/"

NOTES = (
    "Ghana's only licensed Mortgage Finance institution — Bank of Ghana's "
    "register of that category has one entry. NorthStar publish four service "
    "lines: residential property purchase, home improvement, home equity "
    "release and project financing, describing themselves as operating under "
    "the supervision of the Bank of Ghana and as a subsidiary of Northstar "
    "Finance Services, a holding company based in Mauritius. Read from their "
    "own site on 13 September 2026.\n\n"
    "What they do not publish is any price: no interest rate, no minimum, no "
    "loan-to-value ratio and no term. That is the same position as every bank "
    "we have checked except Republic, which publishes four rates on its "
    "mortgage calculator and none on its product pages."
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

    body = {
        "slug": "northstar-home-finance",
        "trading_name": "NorthStar Home Finance",
        "legal_name": "NorthStar Home Finance Company Limited",
        "website": "https://northstarhomefinance.com",
        "contact_email": "info@northstarhomefinance.com",
        "contact_phone": "+233 (0)533 567 231",
        "office_address": "D16 Sekou Toure Street, Ridge Residential Area, Accra",
        "status": "published",
        "notes": NOTES,
    }

    if args.dry_run:
        print()
        print("  NorthStar Home Finance Company Limited")
        print("    Ghana's ONLY licensed Mortgage Finance institution.")
        print()
        print("    Publishes: four service lines, contact details, a statement")
        print("    of BoG supervision, and Mauritius parentage.")
        print()
        print("    Does not publish: rate, minimum, loan-to-value, term.")
        print()
        print("  With this, no Ghanaian institution we have checked — bank or")
        print("  specialist — publishes what a mortgage costs, except Republic")
        print("  on a calculator page.")
        return 0

    existing = call(
        "GET", "/providers?slug=eq.northstar-home-finance&select=id"
    )
    if existing:
        call("PATCH", f"/providers?id=eq.{existing[0]['id']}", body)
        print("  NorthStar Home Finance updated")
    else:
        call("POST", "/providers", body)
        print("  NorthStar Home Finance created")

    # Record the absence, so the disclosure count carries it.
    prov = call("GET", "/providers?slug=eq.northstar-home-finance&select=id")
    if prov:
        call(
            "POST",
            "/provider_disclosure?on_conflict=provider_id,field",
            [
                {
                    "provider_id": prov[0]["id"],
                    "field": "lending_rate",
                    "published_on": None,
                    "checked_on": VERIFIED_ON,
                    "asked_on": None,
                    "answered_on": None,
                    "source_kind": None,
                    "note": None,
                }
            ],
            prefer="resolution=merge-duplicates",
        )
        print("  Absence of a published rate recorded")

    print()
    print(f"  Register: {REGISTER_URL}")
    print(f"  Site: {SITE_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

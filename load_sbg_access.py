"""
load_sbg_access.py — a second broker that answers the question.

WHAT THIS RECORDS
SBG Securities' FAQ carries a question titled "I live outside Ghana, how can I
trade?" and answers it: complete an account opening form and submit it by
email. Their required-documents list separately names "Proof of Foreign
Address (for Non-Resident clients)" and a resident or work permit for
non-Ghanaians.

That is more direct than anything else we have found. Databank Brokerage's form
ACCOMMODATES a non-resident; SBG's FAQ ADDRESSES one. A saver in London
searching that exact question would find an answer.

AND THE INFRASTRUCTURE POINT
The Central Securities Depository states on its own services page that
securities accounts are open to individual investors, corporate investors and
foreign investors — and that every investor must approach an accredited
Depository Participant to open one.

Which matters twice over. It establishes at infrastructure level that a
foreign investor is an eligible category. And it means the route to Ghanaian
shares always runs through a broker, so a broker's willingness is the binding
constraint rather than the depository's.

A CORRECTION WORTH RECORDING
Research handed to us said the CSD Investor Portal supports online securities
account creation from a mobile device or the web. It does not. The portal user
guide that surfaces for that search is Bank of Zambia's — it asks for a
Zambian NRC number and lists Zambia as the country. Ghana's CSD publishes the
opposite: every account is opened through a Depository Participant.

That error is the reason this loader exists rather than a page about a portal.

Usage:
    python load_sbg_access.py --dry-run
    python load_sbg_access.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-09"
SBG_SLUG = "broker-sbg-securities"
SBG_FAQ = "https://www.sbgsecurities.com.gh/sbgsecuritiesghana/sbg-securities/faqs"
CSD_SERVICES = "https://csd.com.gh/services/"

SBG_ACCESS = (
    "SBG Securities publish a FAQ headed \"I live outside Ghana, how can I "
    "trade?\", answered: complete an account opening form and submit it by "
    "email to brokerage@stanbic.com.gh. Their required documents list names "
    "\"Proof of Foreign Address (for Non-Resident clients)\" and a resident or "
    "work permit for non-Ghanaians, alongside passport-sized photographs, a "
    "Ghana Card or passport, proof of physical address and an email indemnity. "
    "Orders are also placed by email using a securities deposit form. Read "
    "from their own material on 9 September 2026. Whether the whole process "
    "can be completed without travelling is not stated, and we have asked."
)

CSD_NOTE = (
    "The Central Securities Depository states that securities accounts are "
    "open to individual investors, corporate investors and foreign investors, "
    "and that every investor must approach an accredited Depository "
    "Participant to open one. So a foreign investor is an eligible category at "
    "infrastructure level, and the route to Ghanaian shares always runs "
    "through a broker — which makes the broker's willingness the binding "
    "constraint rather than the depository's. Read from csd.com.gh on 9 "
    "September 2026."
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
    missing = [
        k
        for k in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
        if not out.get(k)
    ]
    if missing:
        print(f"Missing {', '.join(missing)} — run from the project root.")
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
        print("  SBG Securities — access note:")
        print()
        for part in SBG_ACCESS.split(". "):
            if part.strip():
                print(f"    {part.strip().rstrip('.')}.")
        print()
        print("  Central Securities Depository — provider note:")
        print()
        for part in CSD_NOTE.split(". "):
            if part.strip():
                print(f"    {part.strip().rstrip('.')}.")
        print()
        print("  This makes SBG the second broker with a published position on")
        print("  non-resident access, and the more explicit of the two — a FAQ")
        print("  answering the question rather than a form accommodating it.")
        return 0

    have = call("GET", f"/providers?slug=eq.{SBG_SLUG}&select=id,notes")
    if not have:
        print(f"  {SBG_SLUG} not found.")
        return 1

    row = have[0]
    existing = (row.get("notes") or "").strip()
    call(
        "PATCH",
        f"/providers?id=eq.{row['id']}",
        {
            "access_requirements": SBG_ACCESS,
            "access_verified_on": VERIFIED_ON,
            "website": "https://www.sbgsecurities.com.gh",
            "contact_email": "brokerage@stanbic.com.gh",
            "notes": (f"{existing} {CSD_NOTE}".strip() if existing else CSD_NOTE),
        },
    )
    print("  updated SBG Securities")
    print()
    print("  Two brokers now publish something about non-resident access, out")
    print("  of twenty-four. That is the finding moving, slowly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

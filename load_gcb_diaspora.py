"""
load_gcb_diaspora.py — the widest eligibility and the tightest terms.

THE CONTRAST THIS ONE ADDS
Every other Ghanaian diaspora account we have found is for Ghanaians resident
abroad. GCB's Link2Home reaches further: Ghanaians by birth who took another
citizenship, persons born to at least one Ghanaian parent, and a foreigner
married to a Ghanaian on a joint account.

That second-generation clause matters. A person born in London to a Ghanaian
mother, who has never held a Ghanaian passport, qualifies at GCB and at no
other bank we have checked.

AND THEN THE CONSTRAINTS, WHICH RUN THE OTHER WAY
  "Account is opened with an initial deposit (when in Ghana)"
  "Savings account holders must be present at the branch to effect
   over-the-counter withdrawals"
  "The newly opened (diasporan) account must be funded within 14 days"

So the bank with the broadest definition of who counts as diaspora is also the
one that appears to want you in the country. Zenith, by contrast, state you may
open and operate from anywhere in the world.

Both are published. Neither is wrong. Which suits somebody depends entirely on
whether they visit Ghana, and that is the kind of thing a comparison exists to
surface — no bank would tell you the other's terms.

WHAT IS NOT LOADED
A third-party site describes a Stanbic Diaspora Current Account with a GHS
5,000 minimum. It is not on Stanbic's own pages, the source is over three
years old, and we have loaded only what Stanbic publish themselves.

Usage:
    python load_gcb_diaspora.py --dry-run
    python load_gcb_diaspora.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-14"
PAGE = "https://www.gcbbank.com.gh/personal/savings-accounts/link2home-account"

TERMS = (
    "GCB publish Link2Home, an account for Ghanaians resident abroad, and "
    "their eligibility is the widest of any Ghanaian bank we have found. Four "
    "groups qualify: Ghanaians resident abroad; Ghanaians by birth who have "
    "acquired the citizenship of another country; persons born to at least "
    "one Ghanaian parent; and a foreigner married to a Ghanaian, on joint "
    "accounts.\n\n"
    "That third group is the one worth noticing. Somebody born in London to a "
    "Ghanaian parent, who has never held a Ghanaian passport, qualifies here "
    "and at no other bank on this page.\n\n"
    "The account can be savings or current, in cedis, dollars, pounds or "
    "euros, held individually, jointly or in trust, with Visa or MasterCard "
    "access in Ghana or abroad.\n\n"
    "The constraints run the other way, and they are published plainly. The "
    "account is opened with an initial deposit \"(when in Ghana)\". Savings "
    "account holders must be present at the branch to make over-the-counter "
    "withdrawals. And a newly opened diasporan account must be funded within "
    "14 days.\n\n"
    "So the bank with the broadest view of who counts as diaspora also "
    "appears to expect a visit, where Zenith state an account may be opened "
    "and operated from anywhere in the world. Which suits somebody depends on "
    "whether they travel to Ghana at all.\n\n"
    "Requirements: a completed account opening form, proof of identity such "
    "as an ECOWAS identity card or valid passport, proof of a residential "
    "address abroad, one passport-sized photograph, and an initial deposit on "
    "receiving the account number.\n\n"
    "Read from their own material on 14 September 2026."
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

    prov = call(
        "GET", "/providers?trading_name=ilike.*GCB*&select=id,slug,trading_name"
    )

    if args.dry_run:
        print()
        print("  GCB Bank — Link2Home")
        print()
        print("    WIDEST eligibility of any:")
        print("      Ghanaians resident abroad")
        print("      Ghanaians by birth with another citizenship")
        print("      Persons born to at least one Ghanaian parent")
        print("      A foreigner married to a Ghanaian (joint accounts)")
        print()
        print("    TIGHTEST terms:")
        print("      Opened with an initial deposit '(when in Ghana)'")
        print("      Savings withdrawals need branch presence")
        print("      Must be funded within 14 days")
        print()
        print("    GHS, USD, GBP, EUR. Savings, current or trust.")
        print()
        for p in prov or []:
            print(f"  Provider: {p['slug']} ({p['trading_name']})")
        return 0

    if not prov:
        print("  No GCB provider record found.")
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
                "publisher": "GCB Bank PLC",
                "title": "GCB Link2Home account — terms and qualifying criteria",
                "url": PAGE,
                "retrieved_at": VERIFIED_ON,
            },
            prefer="return=representation",
        )[0]["id"]
    )

    call(
        "PATCH",
        f"/providers?id=eq.{prov[0]['id']}",
        {"access_requirements": TERMS, "access_verified_on": VERIFIED_ON},
    )
    print(f"  GCB Link2Home terms recorded (source {src})")

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
    print("  Four banks now. The interesting thing is that they disagree:")
    print("  GCB take your mother's nationality and want you in a branch;")
    print("  Zenith want a Ghanaian passport and nothing else.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

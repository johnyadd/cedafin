"""
load_databank_brokerage_access.py — correcting a claim we published.

WHAT CHANGES
Our brokers page says not one of the twenty-four licensed dealing members
states whether it will open an account for someone living abroad.

That is no longer true. Databank Brokerage's own page says:

    "Securities trading: We facilitate the trading of securities by both local
     and foreign investors - individuals and institutions alike"

And their brokerage account opening form carries explicit non-resident
provisions: fields for a foreign residential address, foreign mailing address,
foreign telephone and foreign tax identification number, and "Proof of Foreign
Address (for Non-Resident clients)" among the required documents.

WHY BOTH, AND NOT EITHER ALONE
"Foreign investors" is not the same as "Ghanaian diaspora" — read alone it
could mean institutions. The form settles that: a field for an individual's
foreign residential address is not an institutional field.

Neither on its own would be enough. Together they are the clearest published
position on diaspora share access in the Ghanaian market, and we should say so
rather than continue asserting that nobody publishes anything.

WHAT THIS STILL DOES NOT ESTABLISH
That a particular person will be accepted, what documents they will need in
their country, or whether the process can be completed without travelling. A
statement of what a firm facilitates is not a procedure. We have asked.

Usage:
    python load_databank_brokerage_access.py --dry-run
    python load_databank_brokerage_access.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

SLUG = "broker-databank-brokerage"
VERIFIED_ON = "2026-09-05"
BROKERAGE_URL = "https://www.databankgroup.com/brokerage/"

NOTE = (
    "Databank Brokerage state on their own site that they facilitate the "
    "trading of securities by both local and foreign investors, individuals "
    "and institutions alike. Their brokerage account opening form carries "
    "explicit non-resident provisions: fields for a foreign residential "
    "address, foreign mailing address, foreign telephone and foreign tax "
    "identification number, and \"Proof of Foreign Address (for Non-Resident "
    "clients)\" among the required documents. Read from their own material on "
    "5 September 2026. What that means for a particular applicant — which "
    "documents, whether the process can be completed without travelling to "
    "Ghana — is not stated, and we have asked."
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        print("  Databank Brokerage — access note to be recorded:")
        print()
        for chunk in NOTE.split(". "):
            if chunk.strip():
                print(f"    {chunk.strip().rstrip('.')}.")
        print()
        print("  This corrects a live claim. Our brokers page says not one of")
        print("  the twenty-four states whether it will open an account for")
        print("  somebody abroad. Databank does.")
        return 0

    have = call("GET", f"/providers?slug=eq.{SLUG}&select=id,website,notes")
    if not have:
        print(f"  {SLUG} not found — nothing to update.")
        return 1

    row = have[0]
    existing = (row.get("notes") or "").strip()
    merged = f"{existing} {NOTE}".strip() if existing else NOTE

    call(
        "PATCH",
        f"/providers?id=eq.{row['id']}",
        {
            "notes": merged,
            # Their brokerage page rather than the group home page, since that
            # is where the statement is.
            "website": BROKERAGE_URL,
        },
    )
    print("  updated Databank Brokerage")
    print()
    print("  Now correct the brokers page: the claim that not one of the")
    print("  twenty-four publishes anything about access is no longer true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

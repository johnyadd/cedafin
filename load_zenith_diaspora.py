"""
load_zenith_diaspora.py — a stated route from anywhere in the world.

WHY THIS ONE MATTERS MORE THAN THE OTHERS
Almost every Ghanaian provider that says anything about non-residents says
which documents are acceptable. Zenith say where you may be standing.

"This account is targeted at Ghanaians resident abroad and affords them the
opportunity to open and operate an account from anywhere in the world."

That is a statement about eligibility rather than paperwork, and it is the
question the diaspora page exists to answer. Only IC's Liquidity Fund comes
close, and IC state which documents they accept without saying who may apply.

WHAT IT COSTS, AND THE COMPARISON THAT MAKES IT USEFUL
  Zenith — GHS 500 initial, GHS 200 maintained. Documents: a form, one
    photograph, and a copy of a Ghana Card or Ghanaian passport, emailed.
  Absa — no minimum balance at all. But certification of documents by a
    lawyer, notary or court is mandatory for Ghanaians living abroad.

So for somebody in London the cheaper account is probably Zenith, because a
notary costs more than GHS 500. That is the kind of thing a comparison is for
and neither bank could tell you, because neither knows what the other
requires.

WHAT THE SCANNER GOT WRONG
It reported a GHS 10,000 minimum for Zenith. That figure is an income bracket
on their application form, not a minimum. Read the page before believing the
pattern — the scanner's own warning, earned again.

THE LIMIT WORTH STATING
Eligibility is "must be a Ghanaian resident abroad" and 18 or over. This is
not open to non-Ghanaians, and a page about investing from abroad should say
so rather than let a reader assume.

Usage:
    python load_zenith_diaspora.py --dry-run
    python load_zenith_diaspora.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-14"
PAGE = "https://www.zenithbank.com.gh/personal/individual-accounts/"

TERMS = (
    "Zenith publish a Diaspora Account and state plainly who it is for: "
    "Ghanaians resident abroad, who may open and operate an account from "
    "anywhere in the world. Savings, current and fixed deposit accounts can "
    "all be held under it.\n\n"
    "Eligibility is stated rather than implied — the applicant must be a "
    "Ghanaian resident abroad and 18 or over. It is not open to "
    "non-Ghanaians.\n\n"
    "Available in Ghana cedis, US dollars, pounds and euros, though a "
    "Diaspora Savings holder must open a cedi account first before operating "
    "any foreign currency one. Minimum initial deposit is GHS 500 or its "
    "equivalent in foreign exchange, with GHS 200 to be maintained at all "
    "times. Accounts for minors can be opened by a parent or guardian, and "
    "internet banking is included. The current account under the scheme is "
    "cedis only, with a GHS 500 minimum opening balance.\n\n"
    "What is required is light by comparison with other Ghanaian providers: "
    "a downloaded account opening form, one passport-sized photograph, and a "
    "copy of a Ghana Card front and back or a valid international Ghanaian "
    "passport — uploaded by email to diasporacustomerservice@zenithbank.com.gh. "
    "No certification or notarisation is mentioned, where Absa require "
    "certification by a lawyer, notary or court and EDC Stockbrokers require "
    "documents notarised by a foreign authority.\n\n"
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
        "GET",
        "/providers?trading_name=ilike.*zenith*&select=id,slug,trading_name",
    )

    if args.dry_run:
        print()
        print("  Zenith Bank (Ghana) — Diaspora Account")
        print()
        print("    'Open and operate an account from anywhere in the world.'")
        print("    Eligibility: Ghanaian resident abroad, 18 or over.")
        print()
        print("    GHS 500 initial, GHS 200 maintained.")
        print("    Cedis, USD, GBP, EUR — cedi account required first.")
        print("    Form, one photograph, Ghana Card or passport copy, by email.")
        print("    No certification or notarisation required.")
        print()
        print("    Against Absa: no minimum but mandatory certification.")
        print("    For somebody in London, Zenith is probably cheaper —")
        print("    a notary costs more than GHS 500.")
        print()
        for p in prov or []:
            print(f"  Provider: {p['slug']} ({p['trading_name']})")
        return 0

    if not prov:
        print("  No Zenith provider record found.")
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
                "publisher": "Zenith Bank (Ghana)",
                "title": "Zenith Bank Ghana individual accounts — Diaspora Account",
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
    print(f"  Zenith diaspora terms recorded (source {src})")

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
    print("  Two banks now state a diaspora position, and they differ in a way")
    print("  that matters: Absa has no minimum and mandatory certification;")
    print("  Zenith has GHS 500 and an emailed copy of a passport.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

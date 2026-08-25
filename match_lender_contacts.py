"""
match_lender_contacts.py — register contact details onto lending providers.

THE TWO FILES WERE NEVER JOINED
bog_lenders.csv holds name, address, phone, website and email for 797
institutions. apr_banks.csv holds the rates. Providers were created from the
APR names alone, so every lender in the database has a rate and no way to
contact them — which makes the lender pages impossible and the outreach
impossible with them.

WHY A PLAIN NAME MATCH FAILS
The same bank is written differently in each source:

    register                              APR report
    Absa Bank Ghana LTD                   Absa Bank Ghana Limited
    Access Bank (Ghana) Plc               Access Bank Ghana Plc
    Agricultural Development Bank Plc     Agricultural Development Bank Limited
    First Bank (Ghana) LTD                First Bank Ghana Limited

Suffixes differ, brackets come and go. So both sides are normalised — company
suffixes stripped, brackets removed, case and spacing flattened — and matched
on what remains.

NOTHING IS GUESSED
A normalised exact match is applied. Anything that does not match exactly is
REPORTED, not resolved by similarity scoring. Attaching the wrong bank's email
to a rate would send an outreach message to the wrong institution about
numbers that are not theirs — a worse outcome than a blank field, and one
nobody would notice until it embarrassed you.

Usage:
    python match_lender_contacts.py --dry-run
    python match_lender_contacts.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# Stripped before comparison. Order matters: longest first.
SUFFIXES = [
    "public limited company", "company limited", "limited liability",
    "limited", "ltd.", "ltd", "plc.", "plc", "inc.", "inc",
]


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
HDRS = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json", "Prefer": "return=representation"}


def rest(method: str, path: str, body=None, prefer: str | None = None) -> list:
    h = dict(HDRS)
    if prefer:
        h["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}\n  "
                           f"{e.read().decode('utf-8', 'replace')[:300]}") from e


def normalise(name: str) -> str:
    """
    'Access Bank (Ghana) Plc' and 'Access Bank Ghana Limited' both become
    'access bank ghana'.
    """
    s = name.lower().strip()
    s = re.sub(r"[(){}\[\]]", " ", s)          # brackets carry no meaning here
    s = re.sub(r"[.,'&]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for suf in SUFFIXES:
        if s.endswith(" " + suf):
            s = s[: -len(suf) - 1].strip()
            break
    return re.sub(r"\s+", " ", s).strip()


def clean_url(u: str) -> str | None:
    u = (u or "").strip()
    if not u or u.lower() in ("n/a", "na", "-"):
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def clean_email(e: str) -> str | None:
    e = (e or "").strip()
    return e.lower() if "@" in e else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--register", default="bog_lenders.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.register):
        print(f"{args.register} not found — run fetch_bog_registers.py first.")
        return 1

    register = list(csv.DictReader(open(args.register, encoding="utf-8")))
    by_name: dict[str, dict] = {}
    for r in register:
        key = normalise(r.get("name", ""))
        if key and key not in by_name:
            by_name[key] = r
    print(f"{len(register)} register entries, {len(by_name)} distinct names\n")

    # Providers that actually have lending products.
    lending = rest("GET", "/products?market_side=eq.borrow&select=provider_id")
    ids = sorted({p["provider_id"] for p in lending if p.get("provider_id")})
    if not ids:
        print("No lending providers found.")
        return 1

    provs = rest("GET", "/providers?id=in.(" + ",".join(ids) + ")"
                        "&select=id,slug,legal_name,trading_name,website")
    print(f"{len(provs)} lending provider(s) in the database\n")

    matched, missing = [], []
    for p in provs:
        key = normalise(p.get("legal_name") or p.get("trading_name") or "")
        hit = by_name.get(key)
        if hit:
            matched.append((p, hit))
        else:
            missing.append((p, key))

    for p, hit in matched:
        site = clean_url(hit.get("website", ""))
        mail = clean_email(hit.get("email", ""))
        print(f"  ✓ {(p.get('trading_name') or '')[:32]:<34} "
              f"{(site or '—')[:38]:<40} {mail or '—'}")

    if missing:
        print(f"\n  {len(missing)} not matched — reported, not guessed:")
        for p, key in missing:
            print(f"    {(p.get('trading_name') or p.get('legal_name'))[:38]:<40} "
                  f"normalised to '{key}'")
        print("\n  Similar names are NOT auto-resolved. Attaching one bank's")
        print("  email to another's rates would send outreach to the wrong")
        print("  institution about numbers that are not theirs.")

    if args.dry_run:
        print("\nDry run — nothing written.")
        return 0

    updated = 0
    for p, hit in matched:
        patch: dict = {}
        site = clean_url(hit.get("website", ""))
        mail = clean_email(hit.get("email", ""))
        phone = (hit.get("phone") or "").strip()
        addr = (hit.get("address") or "").strip()
        if site and not p.get("website"):
            patch["website"] = site
        if mail:
            patch["contact_email"] = mail
        if phone:
            patch["contact_phone"] = phone
        if addr:
            patch["office_address"] = addr
        if not patch:
            continue
        try:
            rest("PATCH", f"/providers?id=eq.{p['id']}", patch,
                 prefer="return=minimal")
            updated += 1
        except RuntimeError as e:
            # Columns may not exist yet — report rather than fail silently.
            print(f"    {p['slug']}: {str(e)[:120]}")
            break

    print(f"\n  {updated} provider(s) updated with register contact details")
    print("\n  These come from Bank of Ghana's register, which records what an")
    print("  institution filed. A published address is not proof the branch is")
    print("  open, and a general enquiries email is rarely the right person —")
    print("  it is a starting point for outreach, not a verified contact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

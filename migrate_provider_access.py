"""
migrate_provider_access.py — one statement per provider per subject.

THE PROBLEM THIS FIXES
providers.access_requirements holds one block of text per provider, covering
whatever we happened to read. Absa's covers their diaspora accounts AND their
mortgage terms. Fidelity's covers the Non-Resident Ghanaian Account AND the
Power of Attorney a non-resident mortgage applicant needs.

So the diaspora page could not separate "where you can put money" from "where
you can borrow against property". Every available signal was wrong: the
`lending` flag means "has a borrow-side product", which is true of Absa,
Fidelity and GCB — all of whose notes are mostly about accounts.

Any split on the existing data was either hard-coded or wrong. This makes the
distinction a property of the data instead.

WHAT IT DOES
Writes provider_access rows, one per (provider, subject). Most providers get
one row. Absa and Fidelity get two, with their note divided at the sentence
where the subject changes.

WHAT IT DOES NOT DO
Touch providers.access_requirements. The old field stays until the page reads
the new table and nothing else depends on it — a migration that deletes its
own source before the reader is switched over is how data gets lost.

Usage:
    python migrate_provider_access.py --dry-run
    python migrate_provider_access.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-14"

# Providers whose whole note concerns one subject.
WHOLE: dict[str, str] = {
    "zenith-bank-ghana": "deposit",
    "gcb-bank": "deposit",
    "republic-bank-ghana": "borrow",
    "stanbic-bank-ghana": "borrow",
    "first-national-bank-ghana": "borrow",
    "broker-sbg-securities": "invest",
    "broker-edc-stockbrokers": "invest",
    "broker-databank-brokerage": "invest",
}

# Providers whose note covers two subjects, and the sentence where it turns.
# Everything before the marker is the first subject; the marker and everything
# after is the second.
SPLIT: dict[str, tuple[str, str, str]] = {
    "absa-bank-ghana": (
        "deposit",
        "borrow",
        "On mortgages they publish terms and no rate",
    ),
    "fidelity-bank-ghana": (
        "deposit",
        "borrow",
        "One further requirement is worth knowing before applying for the",
    ),
}


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
        print(f"  {e.read().decode('utf-8', 'replace')[:500]}\n")
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = call(
        "GET",
        "/providers?access_requirements=not.is.null"
        "&select=id,slug,trading_name,access_requirements,access_verified_on",
    )
    by_slug = {r["slug"]: r for r in rows or []}

    planned: list[dict] = []
    unhandled: list[str] = []

    for slug, rec in by_slug.items():
        terms = rec.get("access_requirements") or ""
        verified = rec.get("access_verified_on") or VERIFIED_ON

        if slug in SPLIT:
            first, second, marker = SPLIT[slug]
            idx = terms.find(marker)
            if idx == -1:
                unhandled.append(f"{slug} — split marker not found")
                continue
            planned.append(
                {
                    "provider_id": rec["id"],
                    "subject": first,
                    "terms": terms[:idx].strip(),
                    "verified_on": verified,
                    "source_id": None,
                }
            )
            planned.append(
                {
                    "provider_id": rec["id"],
                    "subject": second,
                    "terms": terms[idx:].strip(),
                    "verified_on": verified,
                    "source_id": None,
                }
            )
        elif slug in WHOLE:
            planned.append(
                {
                    "provider_id": rec["id"],
                    "subject": WHOLE[slug],
                    "terms": terms.strip(),
                    "verified_on": verified,
                    "source_id": None,
                }
            )
        else:
            unhandled.append(f"{slug} — no subject assigned")

    if args.dry_run:
        print()
        print(f"  {len(by_slug)} provider(s) with an access note")
        print(f"  {len(planned)} row(s) would be written")
        print()
        for p in planned:
            who = next(
                (s for s, r in by_slug.items() if r["id"] == p["provider_id"]), "?"
            )
            first_line = p["terms"].split(".")[0][:70]
            print(f"    {p['subject']:<8} {who[:28]:<30} {first_line}...")
        if unhandled:
            print()
            print("  NOT HANDLED:")
            for u in unhandled:
                print(f"    {u}")
            print()
            print("  A provider with an access note and no subject would vanish")
            print("  from the page once it reads this table. Assign it first.")
        return 0

    if unhandled:
        print()
        print("  Refusing to write while providers are unassigned:")
        for u in unhandled:
            print(f"    {u}")
        print()
        print("  A partial migration would drop them from the page silently.")
        return 1

    written = 0
    for i in range(0, len(planned), 20):
        batch = planned[i : i + 20]
        call(
            "POST",
            "/provider_access?on_conflict=provider_id,subject",
            batch,
            prefer="resolution=merge-duplicates",
        )
        written += len(batch)

    print(f"  {written} access row(s) written")
    print()
    print("  providers.access_requirements is untouched. Switch the page over,")
    print("  check it, and only then consider retiring the old field.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

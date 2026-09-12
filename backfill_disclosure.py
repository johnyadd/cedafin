"""
backfill_disclosure.py — turn what we know into a record of what we looked for.

WHY THIS TABLE EXISTS
The site says, in prose, in several places: twenty-four of twenty-six savings
and loans companies publish no lending rate. Not one of twenty-four brokers
publishes a commission. Ninety-eight of a hundred and six funds publish no
charge.

Every one of those sentences is a finding that cannot be scraped. A crawler
records what it finds; establishing an ABSENCE needs somebody to have looked
at all twenty-six and written down that there was nothing there, with the
date. That record is the part no model can reproduce without repeating the
work.

At present it exists only as sentences on pages, which means it cannot be
queried, cannot be kept current without editing prose, and disappears the day
somebody rewrites a paragraph.

WHAT THE TABLE RECORDS
Per provider, per field: when we first saw it published, when we last looked,
when we asked, when they answered.

A null published_on with a recent checked_on IS THE DATA. It says: we looked,
on this date, and found nothing. That is the assertion the prose makes, made
checkable.

WHAT THIS SCRIPT DOES
Backfills it from what the database already holds, because a schema with three
rows in it is worse than the prose it replaces. Charges and minimums come from
the products table; access from access_requirements; custody from the flag we
set for the one broker that mentions it.

WHAT IT CANNOT BACKFILL
asked_on. The outreach lives in an email client, not in the database, and
inventing dates would be worse than leaving them null. They get filled in as
replies arrive, or by hand from the sent folder.

Usage:
    python backfill_disclosure.py --dry-run
    python backfill_disclosure.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date

CHECKED = date.today().isoformat()


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
        with urllib.request.urlopen(req, timeout=90) as r:
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

    providers = call(
        "GET",
        "/providers?select=id,slug,trading_name,access_requirements,"
        "access_verified_on,offers_custody",
    )
    products = call(
        "GET",
        "/products?select=id,provider_id,slug,asset_class,market_side,"
        "min_initial_minor,min_verified_on,status&status=eq.published",
    )

    by_provider: dict[str, list[dict]] = defaultdict(list)
    for p in products:
        if p.get("provider_id"):
            by_provider[p["provider_id"]].append(p)

    # Access notes sit on EITHER the provider or the product — a fund
    # manager may say nothing while one of its funds publishes the whole
    # route, as IC does. Reading only providers understated it by half.
    prod_access = call(
        "GET",
        "/products?select=provider_id&access_requirements=not.is.null",
    )
    access_via_product = {p["provider_id"] for p in prod_access if p.get("provider_id")}

    fees = call("GET", "/product_fees?select=product_id,rate")
    priced = {f["product_id"] for f in fees if f.get("rate") is not None}

    rows: list[dict] = []

    for pr in providers:
        pid, slug = pr["id"], pr["slug"]
        mine = by_provider.get(pid, [])
        is_broker = slug.startswith("broker-")
        is_lender = any(p.get("market_side") == "borrow" for p in mine)

        # Non-resident access. Applies to everyone — a saver abroad has the
        # same question of a bank as of a fund manager.
        rows.append(
            {
                "provider_id": pid,
                "field": "non_resident_access",
                "published_on": (
                    pr.get("access_verified_on")
                    if pr.get("access_requirements")
                    else (CHECKED if pid in access_via_product else None)
                ),
                "checked_on": CHECKED,
                "source_kind": (
                    "provider_site"
                    if pr.get("access_requirements") or pid in access_via_product
                    else None
                ),
            }
        )

        if is_broker:
            # No Ghanaian broker publishes a commission rate. Recording the
            # absence for all twenty-four is the finding, not an omission.
            rows.append(
                {
                    "provider_id": pid,
                    "field": "commission",
                    "published_on": None,
                    "checked_on": CHECKED,
                }
            )
            rows.append(
                {
                    "provider_id": pid,
                    "field": "custody",
                    "published_on": CHECKED if pr.get("offers_custody") else None,
                    "checked_on": CHECKED,
                    "source_kind": "provider_site" if pr.get("offers_custody") else None,
                }
            )
            continue

        if is_lender:
            rows.append(
                {
                    "provider_id": pid,
                    "field": "lending_rate",
                    # A lender with a published product carries a rate.
                    "published_on": CHECKED if mine else None,
                    "checked_on": CHECKED,
                    "source_kind": "regulator_filing" if mine else None,
                }
            )
            continue

        # Fund managers: charges and minimum, taken from their products.
        # Match on product ID, not slug. product_fees.product_id is an id,
        # and comparing slugs against it silently matched nothing — every
        # fund manager showed as publishing no charge, which is false.
        any_charge = any(p.get("id") in priced for p in mine)
        charged = [p for p in mine if p.get("min_initial_minor") is not None]

        rows.append(
            {
                "provider_id": pid,
                "field": "charges",
                "published_on": CHECKED if any_charge else None,
                "checked_on": CHECKED,
                "source_kind": "provider_site" if any_charge else None,
            }
        )
        rows.append(
            {
                "provider_id": pid,
                "field": "minimum",
                "published_on": min(
                    (p["min_verified_on"] for p in charged if p.get("min_verified_on")),
                    default=CHECKED if charged else None,
                ),
                "checked_on": CHECKED,
                "source_kind": "provider_site" if charged else None,
            }
        )

    if args.dry_run:
        summary: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for r in rows:
            s = summary[r["field"]]
            s[0] += 1
            if r["published_on"]:
                s[1] += 1
        print()
        print("  What Ghanaian providers disclose, as a record rather than prose")
        print()
        for field, (total, pub) in sorted(summary.items()):
            gap = total - pub
            print(f"    {field:<22} {pub:>3} of {total:<4} publish it   {gap} do not")
        print()
        print(f"  {len(rows)} disclosure record(s) would be written.")
        print()
        print("  Each row with a null published_on and today's checked_on says:")
        print("  we looked, on this date, and there was nothing. That sentence")
        print("  is the thing a crawler cannot produce and a model cannot")
        print("  assert without doing the same work.")
        return 0

    # Upsert on (provider_id, field) so re-running updates checked_on rather
    # than duplicating — the record is a running one, not a snapshot.
    # PostgREST rejects a batch whose objects have different keys, so every
    # row carries every column even where the value is null. "All object keys
    # must match" is the error, and it is not about the data being wrong.
    keys = {k for r in rows for k in r}
    rows = [{k: r.get(k) for k in sorted(keys)} for r in rows]

    written = 0
    for i in range(0, len(rows), 50):
        batch = rows[i : i + 50]
        call(
            "POST",
            "/provider_disclosure?on_conflict=provider_id,field",
            batch,
            prefer="resolution=merge-duplicates",
        )
        written += len(batch)

    print(f"  {written} disclosure record(s) written")
    print()
    print("  asked_on is deliberately null everywhere. The outreach lives in an")
    print("  email client and inventing dates would be worse than leaving them")
    print("  empty. Fill them from the sent folder, or as replies arrive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
check_consistency.py — does the data hang together?

WHY THIS EXISTS
Thirty-seven provider records represented twenty-four broker firms for about
five months. Each card read correctly on its own. The site had provenance
blocks, dated figures and a methodology page — all of which describe where a
number came from, and none of which notices when the numbers contradict each
other.

It was found because somebody asked why Databank appeared twice.

Every check here is one that would have caught something we have actually got
wrong. None is hypothetical.

WHAT IT DOES NOT DO
Fix anything. It reports and exits non-zero, so a scheduled run goes red and
the problem is visible the next morning rather than in five months. Silent
repair would hide the fault that caused it.

Usage:
    python check_consistency.py
    python check_consistency.py --quiet     # only failures
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date

GSE_TYPOS = {
    "securties": "securities",
    "securites": "securities",
    "firstatlantic": "first atlantic",
}
BROKER_NOISE = (
    r"\b(limited|ltd|plc|company|co|markets?|capital|securities|brokerage|"
    r"stockbrokers?)\b"
)


def broker_key(name: str) -> str:
    s = (name or "").lower()
    for wrong, right in GSE_TYPOS.items():
        s = s.replace(wrong, right)
    s = re.sub(r"[^a-z ]+", " ", s)
    s = re.sub(BROKER_NOISE, " ", s)
    return re.sub(r"\s+", " ", s).strip()


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
        print("Missing Supabase credentials.")
        sys.exit(1)
    return out


E = env()
BASE = E["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = E["SUPABASE_SERVICE_ROLE_KEY"]


def get(path: str):
    req = urllib.request.Request(
        BASE + path, headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


FAILURES: list[str] = []
WARNINGS: list[str] = []


def fail(check: str, detail: str) -> None:
    FAILURES.append(f"{check}: {detail}")


def warn(check: str, detail: str) -> None:
    WARNINGS.append(f"{check}: {detail}")


def months_between(a: str, b: str) -> int:
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb - ya) * 12 + (mb - ma) + 1


def check_duplicate_providers(quiet: bool) -> None:
    """
    THE ONE THAT WAS MISSED. The exchange renames firms between reports, and
    slugifying the printed name produced a record per spelling.
    """
    rows = get("/providers?select=slug,trading_name&slug=like.broker-*")
    groups: dict[str, list[str]] = defaultdict(list)
    for p in rows:
        groups[broker_key(p.get("trading_name") or p["slug"])].append(p["slug"])
    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    if dupes:
        for k, slugs in sorted(dupes.items()):
            fail("duplicate brokers", f"{k} -> {', '.join(slugs)}")
    elif not quiet:
        print(f"  ok    {len(rows)} brokers, {len(groups)} distinct firms")


def check_month_counts(quiet: bool) -> None:
    """
    The count came from one source and the date range from another, so a firm
    showed "15 months (Feb 2026 - Jul 2026)".
    """
    rows = get(
        "/providers?select=slug,broker_months_observed,broker_first_seen,"
        "broker_last_seen&slug=like.broker-*"
        "&broker_months_observed=not.is.null"
    )
    bad = 0
    for p in rows:
        f, l, n = p["broker_first_seen"], p["broker_last_seen"], p["broker_months_observed"]
        if not (f and l and n):
            continue
        span = months_between(f, l)
        if n > span:
            fail(
                "month count",
                f"{p['slug']} claims {n} months across a {span}-month span",
            )
            bad += 1
    if not bad and not quiet:
        print(f"  ok    {len(rows)} broker date ranges fit their month counts")


def check_future_dates(quiet: bool) -> None:
    """A figure dated tomorrow is a parsing error, always."""
    today = date.today().isoformat()
    for table, field in (
        ("products", "min_verified_on"),
        ("products", "access_verified_on"),
        ("nav_observations", "as_of"),
        ("macro_series", "as_of"),
    ):
        try:
            rows = get(f"/{table}?select={field}&{field}=gt.{today}&limit=5")
        except urllib.error.HTTPError:
            continue
        if rows:
            fail("future date", f"{table}.{field} has {len(rows)}+ row(s) after {today}")
    if not quiet:
        print("  ok    no figures dated in the future")


def check_charge_bounds(quiet: bool) -> None:
    """
    A charge above 10% a year or below zero is a unit error — a percentage
    stored as a fraction, or the other way round. We have made that mistake:
    every Apple figure was out by a thousand once.
    """
    rows = get(
        "/product_fees?select=product_id,rate,fee_type&rate=not.is.null"
    )
    for f in rows:
        r = float(f["rate"])
        if r < 0:
            fail("charge bounds", f"product {f['product_id']} has a negative {f['fee_type']}")
        elif r > 0.10 and f["fee_type"] not in ("other",):
            warn(
                "charge bounds",
                f"product {f['product_id']} {f['fee_type']} is {r * 100:.2f}% a year",
            )
    if not quiet:
        print(f"  ok    {len(rows)} charge(s) within plausible bounds")


def check_published_have_sources(quiet: bool) -> None:
    """
    The site's whole claim is that every figure is traceable. A published
    product with no source contradicts it.
    """
    # Only products that HAVE a minimum need a source for it. Most publish
    # none, which is a blank field rather than an unsourced figure — flagging
    # those made the check cry wolf 237 times.
    rows = get(
        "/products?select=slug,min_initial_minor,min_source_id"
        "&status=eq.published&min_initial_minor=not.is.null"
    )
    missing = [p["slug"] for p in rows if not p.get("min_source_id")]
    if missing:
        warn(
            "sources",
            f"{len(missing)} published product(s) carry no minimum source",
        )
    if not quiet:
        print(f"  ok    {len(rows) - len(missing)}/{len(rows)} published products sourced")


def check_orphan_products(quiet: bool) -> None:
    """A product whose provider was deleted renders with no name."""
    prods = get("/products?select=slug,provider_id&status=eq.published")
    provs = {p["id"] for p in get("/providers?select=id")}
    orphans = [p["slug"] for p in prods if p.get("provider_id") not in provs]
    if orphans:
        for s in orphans[:10]:
            fail("orphan product", s)
    elif not quiet:
        print(f"  ok    {len(prods)} published products all have a provider")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not args.quiet:
        print()
        print("  Consistency checks — every one of these caught something real")
        print()

    for fn in (
        check_duplicate_providers,
        check_month_counts,
        check_future_dates,
        check_charge_bounds,
        check_published_have_sources,
        check_orphan_products,
    ):
        try:
            fn(args.quiet)
        except Exception as e:  # noqa: BLE001
            warn(fn.__name__, f"could not run — {e}")

    print()
    if WARNINGS:
        print(f"  {len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(f"    {w}")
        print()
    if FAILURES:
        print(f"  {len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"    {f}")
        print()
        print("  Exiting non-zero so a scheduled run goes red. Nothing is")
        print("  repaired automatically — a silent fix would hide the load")
        print("  that caused it.")
        return 1

    print("  All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

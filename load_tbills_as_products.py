"""
load_tbills_as_products.py — Government of Ghana T-bills as comparable products.

WHY THIS IS THE HIGHEST-VALUE HOUR LEFT
The rates are already in macro_series and doing nothing but sitting behind a
real-return calculation. As products they change what the site can say. Today
the money market page compares Stanbic Cash Trust against itself. With T-bills
in it, a saver sees:

    Stanbic Cash Trust        2.25% a year in charges
    364-day Treasury bill    12.99%, no charges at all

That is the comparison a Ghanaian with GH1,000 actually faces, and nobody
publishes it side by side.

A T-BILL IS NOT A FUND, and the differences are not cosmetic:

  NO CHARGES. Not "charges not published" — genuinely none. The comparison page
  currently renders a missing charge in amber, which would read as a disclosure
  failure on the one product that has nothing to disclose. It needs a zero, and
  a page that shows zero rather than a warning.

  NO MANAGER. The provider is the Government of Ghana, and there is no
  custodian, no trustee, no expense ratio. Those fields stay null and mean it.

  A YIELD, NOT A PRICE. A bill is bought at a discount and redeems at par.
  nav is null and yield_annualised carries the rate, which is exactly the shape
  metrics.py already handles for yield-quoted money market funds — it reports
  the yield and leaves volatility and drawdown absent rather than inventing
  them from a series that does not exist.

  A FIXED TERM. 91, 182 or 364 days, then your money comes back. That is a real
  difference from a daily-dealing fund and it belongs on the page: lock_in_days
  carries it.

WHAT THIS DOES NOT CLAIM
Whether a saver can buy bills directly, and at what minimum, depends on the
route — a bank, a broker, or the Bank of Ghana's own channel — and none of that
is verified here. The products carry no minimum rather than a guessed one.

Usage:
    python load_tbills_as_products.py --dry-run
    python load_tbills_as_products.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BILLS = [
    {"slug": "gog-treasury-bill-91", "name": "91-day Treasury Bill",
     "series": "GH_TBILL_91", "days": 91},
    {"slug": "gog-treasury-bill-182", "name": "182-day Treasury Bill",
     "series": "GH_TBILL_182", "days": 182},
    {"slug": "gog-treasury-bill-364", "name": "364-day Treasury Bill",
     "series": "GH_TBILL_364", "days": 364},
]

PROVIDER = {
    "slug": "government-of-ghana",
    "legal_name": "Government of Ghana",
    "trading_name": "Government of Ghana",
    "website": "https://www.bog.gov.gh",
    "status": "published",
}


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    plans = []
    for b in BILLS:
        rows = rest("GET", f"/macro_series?series_code=eq.{b['series']}"
                           f"&select=as_of,value,source_id&order=as_of")
        if not rows:
            print(f"  {b['name']}: no {b['series']} data — skipped")
            continue
        plans.append({**b, "points": rows})
        latest = rows[-1]
        print(f"  {b['name']:<24} {len(rows):>3} rate point(s), "
              f"latest {latest['value'] * 100:.4f}% at {latest['as_of']}")

    if not plans:
        print("\nNothing to load. Run load_benchmarks.py first.")
        return 1

    if args.dry_run:
        print("\nWould create 1 provider and "
              f"{len(plans)} products with zero charges.")
        print("Dry run — nothing written.")
        return 0

    existing = rest("GET", f"/providers?slug=eq.{PROVIDER['slug']}&select=id")
    provider_id = (existing[0]["id"] if existing
                   else rest("POST", "/providers", PROVIDER)[0]["id"])
    print(f"\n  provider: Government of Ghana")

    made = 0
    for p in plans:
        found = rest("GET", f"/products?slug=eq.{p['slug']}&select=id")
        if found:
            pid = found[0]["id"]
        else:
            pid = rest("POST", "/products", {
                "slug": p["slug"], "provider_id": provider_id, "name": p["name"],
                "share_class": "main",
                "legal_structure": "treasury_bill",
                # Peer group is derived from asset_class + currency, so bills
                # sit in government_security:GHS — deliberately NOT alongside
                # money market funds. A comparison page can show both, but a
                # sovereign bill and a managed fund are not the same risk and
                # should not be ranked against each other as though they were.
                "asset_class": "government_security",
                "currency": "GHS",
                "dealing_frequency": "at_maturity",
                "lock_in_days": p["days"],
                "distributes": False,
                "objective": (
                    f"Direct lending to the Government of Ghana for {p['days']} "
                    f"days. Bought at a discount and redeemed at face value. No "
                    f"management charge, no custody charge, and your money is "
                    f"returned at maturity rather than on demand."
                ),
                "status": "published",
            })[0]["id"]
            made += 1

        # ZERO charges, recorded explicitly. A null would render as "not
        # published", which on a T-bill would be actively misleading — there is
        # nothing to publish because there is nothing to charge.
        rest("DELETE", f"/product_fees?product_id=eq.{pid}", prefer="return=minimal")
        first_source = p["points"][0]["source_id"]
        rest("POST", "/product_fees", [{
            "product_id": pid, "fee_type": ft, "rate": 0, "flat_minor": None,
            "basis": "annual_nav",
            "conditions": "No charge. Treasury bills carry no management or "
                          "custody fee — you lend directly to the government.",
            "effective_from": p["points"][0]["as_of"], "effective_to": None,
            "source_id": first_source,
            "verified_on": p["points"][-1]["as_of"],
        } for ft in ("management", "custody", "stated_charges")])

        # Yield, not price. metrics.py already handles yield-quoted series:
        # it reports the rate and leaves volatility and drawdown absent rather
        # than manufacturing them.
        obs = [{
            "product_id": pid, "as_of": r["as_of"], "nav": None,
            "yield_annualised": r["value"], "basis": "single",
            "series_kind": "quoted", "source_id": r["source_id"],
        } for r in p["points"]]
        rest("POST", "/nav_observations", obs,
             prefer="return=minimal,resolution=ignore-duplicates")

        print(f"  {p['name']:<24} {len(obs)} observation(s), charges 0.00%")

    print(f"\n  {made} product(s) created, {len(plans) - made} already existed")
    print("  T-bills sit in government_security:GHS, not with money market")
    print("  funds — a sovereign bill and a managed fund are different risks.")
    print("\n  NOTE: no minimum investment is recorded. How a saver actually")
    print("  buys these — bank, broker, or BoG directly — and at what minimum")
    print("  is not verified, so it is left blank rather than guessed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

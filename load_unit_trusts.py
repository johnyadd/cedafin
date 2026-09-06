"""
load_unit_trusts.py — thirty-one retail funds this site did not know existed.

HOW THEY WERE MISSED
The SEC register publishes eighteen category pages. Our scraper knew about
six, because those were the six somebody thought to list when it was written.
Reading the register's own index turned up twelve more, including a page of
thirty-three unit trusts.

Two of the thirty-three are already here — Stanbic Cash Trust and Stanbic
Income Fund Trust, loaded from their factsheets. The other thirty-one are new,
and they are ordinary retail funds a Ghanaian saver could buy.

WHAT THIS LOADS
Names, managers and websites, which is all the register gives. No charges, no
minimums, no returns — those come from factsheets, and asking for them is the
next job.

That leaves them looking like the sixty-seven funds already listed with blank
fields, and the ratio this site publishes moves from eight of seventy-five to
eight of a hundred and six. That is not a step backwards: the catalogue is
more complete and the gap is more accurately measured.

HOW THEY ARE CLASSIFIED
From each trust's own name and nothing else. "Fidelity Fixed Income Trust" is
fixed income because it says so. Eleven of the thirty-one — "Legacy Unit
Trust", "Richie Rich Unit Trust", "Golden Eagle Unit Trust" — say nothing
about what they hold, and are loaded without an asset class rather than
guessed at.

"Gold Fund Unit Trust" is the one worth naming. It might be a commodity fund
or it might be a fund called Gold. Assuming would be exactly the error this
site exists to point out, so it stays unclassified until somebody tells us.

ONE THING THE REGISTER ITSELF GETS ODD
Republic Real Estate Investment Trust is registered under Unit Trusts, not
under the separate REIT Funds page. So the SEC lists four REITs across two
registers, which is worth knowing if you are counting them.

Usage:
    python load_unit_trusts.py --dry-run
    python load_unit_trusts.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-05"
REGISTER_URL = "https://licensees.sec.gov.gh/licensees/UnitTrust.php"

# (trust name, manager name, manager website)
#
# Managers are taken from the website the register gives, since the register
# does not name them separately. Where several trusts share a site they share
# a manager, which is how they are grouped here.
TRUSTS: list[tuple[str, str, str]] = [
    ("AIM Freedom Fixed Income Trust", "Ashfield Investment Managers", "ashfieldinvest.com"),
    ("AIM Multi-Asset Trust", "Ashfield Investment Managers", "ashfieldinvest.com"),
    ("Algebra Income Trust", "Algebra Capital", "algebracapital.com.gh"),
    ("Bora Balanced Unit Trust", "Bora Advisors", "boradvisors.com"),
    ("Bora Fixed Income Unit Trust", "Bora Advisors", "boradvisors.com"),
    ("Bora Global Balanced Trust", "Bora Advisors", "boradvisors.com"),
    ("Cal Advantage Balanced Unit Trust", "CAL Asset Management", "calassetmanagement.net"),
    ("Cal Benefit Fixed Income Unit Trust", "CAL Asset Management", "calassetmanagement.net"),
    ("EDC Ghana Africa Cash Trust", "EDC Investments (Ecobank)", "ecobank.com"),
    ("EDC Ghana Fixed Income Unit Trust", "EDC Investments (Ecobank)", "ecobank.com"),
    ("EDC Ghana Growth Trust", "EDC Investments (Ecobank)", "ecobank.com"),
    ("EDC Ghana Money Market Unit Trust", "EDC Investments (Ecobank)", "ecobank.com"),
    ("Fidelity Balanced Trust", "Fidelity Asset Management", "fidelitybank.com.gh"),
    ("Fidelity Fixed Income Trust", "Fidelity Asset Management", "fidelitybank.com.gh"),
    ("Fidelity Money Market Trust", "Fidelity Asset Management", "fidelitybank.com.gh"),
    ("Gold Fund Unit Trust", "First Finance Company", "firstfinancecompany.com"),
    ("Golden Eagle Unit Trust", "GCB Capital", "gcbcapital.com.gh"),
    ("Legacy Unit Trust", "IFS Capital Management", "ifscapitalgh.com"),
    ("My Wealth Unit Trust", "IFS Capital Management", "ifscapitalgh.com"),
    ("Nimed Lifetime Unit Trust", "Nimed Capital", "nimedcapital.com"),
    ("PSL Fixed Income Unit Trust", "Prudential Securities", "prudentialsecurities.com.gh"),
    ("Republic Equity Trust", "Republic Investments Ghana", "republicinvestmentsgh.com"),
    ("Republic Future Plan Trust", "Republic Investments Ghana", "republicinvestmentsgh.com"),
    ("Republic Real Estate Investment Trust", "Republic Investments Ghana", "republicinvestmentsgh.com"),
    ("Republic Unit Trust", "Republic Investments Ghana", "republicinvestmentsgh.com"),
    ("Republic Wealth Trust", "Republic Investments Ghana", "republicinvestmentsgh.com"),
    ("Richie Rich Unit Trust", "IFS Capital Management", "ifscapitalgh.com"),
    ("Sentinel Africa Eurobond Trust", "Sentinel Asset Management", "sentinelaml.com"),
    ("Sentinel Ghana Fixed IncomeTrust", "Sentinel Asset Management", "sentinelaml.com"),
    ("Tesah Treasury Trust", "Tesah Capital", "tesahcapital.com"),
    ("Unisecurities Unit Trust", "First Finance Company", "firstfinancecompany.com"),
]


def asset_class(name: str) -> str | None:
    """
    From the trust's own name, or nothing.

    A name that does not say what the fund holds gets no class. Eleven of the
    thirty-one fall in that group, and a guess there would be a fact this site
    invented.
    """
    n = name.lower()
    if "real estate" in n:
        return "real_estate"
    if "money market" in n or "cash" in n or "treasury" in n:
        return "money_market"
    if "fixed income" in n or "eurobond" in n:
        return "fixed_income"
    if "balanced" in n or "multi-asset" in n:
        return "balanced"
    if "equity" in n or "growth" in n:
        return "equity"
    return None


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower())
    return s.strip("-")


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
        from collections import Counter

        counts: Counter = Counter()
        managers = {m for _, m, _ in TRUSTS}
        for name, manager, _ in TRUSTS:
            k = asset_class(name)
            counts[k or "not stated in the name"] += 1
            print(f"  {name[:40]:<42} {manager[:26]:<28} {k or '—'}")
        print()
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"    {v:>2}  {k}")
        print()
        print(f"  {len(TRUSTS)} trusts across {len(managers)} managers.")
        print()
        print("  Eleven names say nothing about what the fund holds and are")
        print("  loaded without a class rather than guessed at — including")
        print("  'Gold Fund Unit Trust', which may or may not hold gold.")
        return 0

    src = call("GET", f"/sources?url=eq.{REGISTER_URL}&select=id")
    if src:
        source_id = src[0]["id"]
    else:
        source_id = call(
            "POST",
            "/sources",
            {
                "kind": "regulator_publication",
                "publisher": "Securities and Exchange Commission, Ghana",
                "title": "Register of licensed unit trusts",
                "url": REGISTER_URL,
                "retrieved_at": VERIFIED_ON,
            },
            prefer="return=representation",
        )[0]["id"]
    print(f"  source {source_id}")

    # Managers first, so trusts can be attributed rather than sitting under a
    # placeholder like the sixty-seven already here.
    provider_ids: dict[str, str] = {}
    for _, manager, site in TRUSTS:
        if manager in provider_ids:
            continue
        slug = slugify(manager)
        have = call("GET", f"/providers?slug=eq.{slug}&select=id")
        if have:
            provider_ids[manager] = have[0]["id"]
            continue
        made = call(
            "POST",
            "/providers",
            {
                "slug": slug,
                "legal_name": manager,
                "trading_name": manager,
                "website": f"https://{site}",
                "status": "published",
                "notes": (
                    "From the SEC register of licensed unit trusts. Charges, "
                    "minimums and returns not yet obtained — asked."
                ),
            },
            prefer="return=representation",
        )
        provider_ids[manager] = made[0]["id"]
    print(f"  {len(provider_ids)} manager(s)")

    added = skipped = 0
    for name, manager, _ in TRUSTS:
        slug = slugify(name)
        if call("GET", f"/products?slug=eq.{slug}&select=id"):
            skipped += 1
            continue
        row = {
            "slug": slug,
            "name": name,
            "provider_id": provider_ids[manager],
            "currency": "GHS",
            "market_side": "invest",
            "legal_structure": "unit_trust",
            "status": "published",
            "eligibility_notes": (
                "Licensed unit trust, from the SEC register. We hold no "
                "charges, minimum or return history for it yet."
            ),
        }
        cls = asset_class(name)
        if cls:
            row["asset_class"] = cls
        call("POST", "/products", row)
        added += 1

    print()
    print(f"  {added} added, {skipped} already here")
    print()
    print("  The catalogue is now larger and the gap in it is larger too —")
    print("  which is the honest position rather than a worse one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

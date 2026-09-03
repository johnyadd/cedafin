"""
load_blackstar.py — attributing six funds to the manager that runs them.

WHY THIS EXISTS
Sixty-two of the seventy-five Ghanaian funds catalogued sit under a
placeholder provider called "Provider not yet verified". The SEC register
lists fund names without reliably linking them to the firms that manage them,
and guessing would be worse than leaving them unattributed.

Black Star Advisors Limited publishes its own fund list. Six funds, named on
their own site, under their own management. That is attribution from the
manager rather than inference from a register, which is the standard this
site holds itself to.

WHAT THIS LOADS, AND WHAT IT DELIBERATELY DOES NOT
Loaded: the provider, its published contact details, and six funds attributed
to it by asset class.

NOT loaded: charges, minimums, dealing frequency, returns. The only fee figure
findable was 2.50% on the Plus Income Fund from an April 2022 third-party
page. Four years old, from a source that is not the manager, and publishing it
as current would be exactly the unstated staleness this site criticises
elsewhere. The fields stay blank until Black Star sends them or publishes them
where they can be dated.

A fund attributed with blank fields is better than one attributed to nobody:
the name is right, the manager is right, and the ask becomes specific.

WHY THEIR CONTACT DETAILS COME FROM THEIR SITE AND NOT THE REGISTER
The SEC register gives blackstarbrokerage.com.gh for Black Star Brokerage.
That domain has no MX record — mail to it fails with SERVFAIL, which is how we
found out. Their own contact page gives clientservices@blackstargroup.ai.

That is the second SEC register email found to be dead, after Databank's. The
register is a starting point, not a verified source.

Usage:
    python load_blackstar.py --dry-run
    python load_blackstar.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

SLUG = "black-star-advisors"

PROVIDER = {
    "slug": SLUG,
    "legal_name": "Black Star Advisors Limited",
    "trading_name": "Black Star Advisors",
    "website": "https://blackstargroup.ai",
    # From their own contact page. The SEC register's address for the
    # brokerage arm bounces — see the module docstring.
    "contact_email": "clientservices@blackstargroup.ai",
    "contact_phone": "+233 30 222 7698 / +233 59 699 4904",
    # Column is office_address, not address — the insert failed with a 400
    # until this matched the schema.
    "office_address": "The Rhombus, Plot 24 Tumu Avenue, Kanda Estates, Accra",
    "status": "published",
    "notes": (
        "Manages six mutual funds and publishes five of its own indices, "
        "including a Ghana Equity Total Return Index that accounts for "
        "dividends as well as capital gains. Licensed by the SEC as Black "
        "Star Advisors (asset management) and Black Star Brokerage. Charges "
        "and minimums not yet obtained — asked."
    ),
}

# Names and asset classes as Black Star publishes them. Nothing inferred
# beyond the mapping of their own category headings to ours.
FUNDS = [
    ("Fixed Income Alpha Fund", "fixed_income"),
    ("Delta Fund", "fixed_income"),
    ("Plus Balanced Fund", "balanced"),
    ("Enhanced Equity Beta Fund", "equity"),
    ("Christian Community Mutual Fund", "equity"),
    ("Plus Income Fund", "money_market"),
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
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def slugify(name: str) -> str:
    s = name.lower()
    for ch in " /":
        s = s.replace(ch, "-")
    return "".join(c for c in s if c.isalnum() or c == "-").strip("-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        print(f"  provider: {PROVIDER['legal_name']}")
        print(f"    {PROVIDER['contact_email']}")
        print(f"    {PROVIDER['website']}")
        print()
        for name, cls in FUNDS:
            print(f"  {name:<38} {cls}")
        print()
        print("  Charges, minimums and returns left blank — no dated source.")
        return 0

    existing = call("GET", f"/providers?slug=eq.{SLUG}&select=id")
    if existing:
        pid = existing[0]["id"]
        call("PATCH", f"/providers?id=eq.{pid}", PROVIDER)
        print(f"  updated provider {SLUG}")
    else:
        created = call(
            "POST", "/providers", PROVIDER, prefer="return=representation"
        )
        pid = created[0]["id"]
        print(f"  created provider {SLUG}")

    made = 0
    for name, cls in FUNDS:
        slug = f"blackstar-{slugify(name)}"
        if call("GET", f"/products?slug=eq.{slug}&select=id"):
            print(f"    exists: {name}")
            continue
        call(
            "POST",
            "/products",
            {
                "slug": slug,
                "name": name,
                "provider_id": pid,
                "asset_class": cls,
                "currency": "GHS",
                "market_side": "invest",
                "legal_structure": "mutual_fund",
                # Draft, not published: a fund with no charge, no minimum and
                # no return has nothing to compare on yet. Attribution is the
                # gain here, not a comparison row.
                "status": "draft",
            },
        )
        made += 1
        print(f"    created: {name}")

    print()
    print(f"  {made} fund(s) attributed to {PROVIDER['trading_name']}")
    print()
    print("  Left as drafts deliberately. A fund with no charge, no minimum")
    print("  and no return cannot be compared — but it is now attributed to")
    print("  the manager that runs it rather than sitting under 'Provider not")
    print("  yet verified', and the ask when we write to them is specific.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

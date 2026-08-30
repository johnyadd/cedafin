"""
load_newgold_ter.py — NewGold's published charge, and what it means beside a coin.

THE FIGURE
0.30% total expense ratio. Absa's own factsheet defines it as the portion of
the ETF's assets paid out for services in managing the fund, over a 12-month
rolling period — and states plainly that it EXCLUDES brokerage and
transactional costs. So 0.30% is what the fund charges; what a Ghanaian
licensed dealing member adds on top is still unpublished, by any of them.

THE COMPARISON NOBODY MAKES
Two ways to own gold in Ghana, charged in completely different shapes:

    Ghana Gold Coin, 1 oz     3.58% once, on purchase
    Ghana Gold Coin, ¼ oz     7.75% once, on purchase
    NewGold ETF               0.30% every year

A one-off premium and an annual fee cannot be compared without a holding
period. Divide one by the other and you get the year at which they cross:

    3.58 / 0.30 ≈ 12 years
    7.75 / 0.30 ≈ 26 years

Hold gold for longer than that and the coin is cheaper. Hold it for less — which
is most people, most of the time — and the ETF is cheaper, dramatically so for
anyone who would otherwise buy the small coin. And the entry prices differ by a
factor of thirty: GH¢462 against GH¢13,803.

SHARIA COMPLIANCE, PROPERLY SOURCED
Absa Bank's Shari'ah Board — specialist jurists in Islamic law — ruled in March
2008 that the NewGold ETF complies with Shariah Law. That is the issuer's own
documented claim, not our inference, which is the standard required before this
field is set to true anywhere in this database.

The Ghana Gold Coin stays NULL. Gold has an accepted AAOIFI standard and the
coin is 99.99% bullion, so it very likely qualifies — but Bank of Ghana makes
no such claim, and asserting it on our own reasoning is exactly what this site
refuses to do everywhere else.

Usage:
    python load_newgold_ter.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

TER_PCT = 0.30

TER_CONDITIONS = (
    "Total expense ratio as published by Absa. Charged annually against fund "
    "assets. EXCLUDES brokerage and transaction costs — a Ghanaian licensed "
    "dealing member charges separately and none of them publish their rates."
)

SHARIA_BASIS = (
    "Absa Bank's Shari'ah Board, made up of specialist jurists in Islamic law, "
    "ruled in March 2008 that the NewGold ETF complies with Shariah Law. "
    "Stated by the issuer in its own factsheet."
)

ELIGIBILITY = (
    "Bought through a licensed dealing member of the Ghana Stock Exchange. "
    "The 0.30% fund charge is annual; brokerage is charged on top and is not "
    "published by any Ghanaian broker. Each unit is roughly 1/100 oz of gold "
    "bullion held with a custodian."
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
    prod = rest("GET", "/products?slug=eq.gse-gld&select=id,name,status")
    if not prod:
        print("NewGold ETF not found — run load_gse.py --etf-only first.")
        return 1
    pid = prod[0]["id"]

    title = "NewGold ETF Minimum Disclosure Document"
    src = rest("GET", "/sources?title=eq." + urllib.parse.quote(title) + "&select=id")
    source_id = src[0]["id"] if src else rest("POST", "/sources", {
        "kind": "provider_factsheet",
        "publisher": "Absa Corporate and Investment Banking",
        "title": title,
    })[0]["id"]

    existing = rest(
        "GET", f"/product_fees?product_id=eq.{pid}&fee_type=eq.ter&select=id")
    if not existing:
        rest("POST", "/product_fees", [{
            "product_id": pid,
            "fee_type": "ter",
            "rate": TER_PCT / 100,
            "basis": "annual_nav",
            "conditions": TER_CONDITIONS,
            "effective_from": "2026-07-31",
            "effective_to": None,
            "source_id": source_id,
            "verified_on": "2026-07-31",
        }], prefer="return=minimal")
        print(f"  TER {TER_PCT}% added")
    else:
        print("  TER already present")

    rest("PATCH", f"/products?id=eq.{pid}", {
        "sharia_compliant": True,
        "sharia_basis": SHARIA_BASIS,
        "eligibility_notes": ELIGIBILITY,
        "distributes": False,
        "status": "published",
    }, prefer="return=minimal")
    print("  Sharia ruling, eligibility note and distribution flag set")

    print(f"\n  NewGold: {TER_PCT}% a year.")
    print(f"  Ghana Gold Coin: 3.58% once (1 oz), 7.75% once (¼ oz).")
    print(f"\n  Break-even holding period:")
    for label, prem in (("1 oz coin", 3.58), ("½ oz coin", 4.83), ("¼ oz coin", 7.75)):
        print(f"    vs {label:<10} {prem / TER_PCT:>5.1f} years")
    print("\n  Below those, the ETF is cheaper. Above them, the coin is.")
    print("  Most people hold gold for far less than twelve years, and anyone")
    print("  who would buy the quarter-ounce coin is comparing 7.75% once")
    print("  against 0.30% a year — the ETF stays cheaper for 26 years.")
    print("\n  Neither figure includes what a Ghanaian broker charges to buy")
    print("  the ETF. None of the 35 licensed dealing members publishes a rate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

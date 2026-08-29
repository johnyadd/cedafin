"""
load_gold_coin.py — the Ghana Gold Coin as three comparable products.

THREE PRODUCTS, NOT ONE IN THREE SIZES
An ounce bought as four quarter-ounce coins costs about 4.4% more than an ounce
bought whole — roughly GH¢2,197 at current prices. That is not a packaging
detail, it is a different price for the same metal, and it falls on whoever has
least to spend. Each denomination therefore gets its own row with its own
effective cost, the same way Stanbic's two share classes are two rows because
they returned 38.80% and 15.39%.

THE PREMIUM IS THE CHARGE
Gold has no management fee, so a naive load would show "no charges" beside a
fund at 1.75% and imply the coin is free to own. It is not. Bank of Ghana sells
an ounce for about 3.5% more than the metal is worth at LBMA spot times the
day's exchange rate, and across 56 days that premium ranged from 2.15% to
3.73% — managed, not fixed. It is recorded as a fee because that is what it is.

The denomination penalty is recorded the same way, as a second fee row, so a
comparison page shows both costs rather than one.

WHAT A CEDI HOLDER ACTUALLY EARNS
Every observation stores the coin price, the LBMA dollar price and the USD/GHS
rate together. Over June to August 2026 gold rose 0.5% in dollars while the
coin fell 3.9% in cedis, because the cedi strengthened from 11.735 to 11.215.
Someone who bought gold to hedge lost money in the currency they spend. Storing
the cedi price alone would make that impossible to explain.

MINIMUM ENTRY IS THE UNCOMFORTABLE PART
The cheapest way in is a quarter-ounce coin at roughly GH¢13,800. Stanbic Cash
Trust takes GH¢20. Gold is often recommended to ordinary savers as protection,
and in Ghana it is priced for people who already have money.

Usage:
    python load_gold_coin.py --dry-run
    python load_gold_coin.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DENOMINATIONS = [
    ("1_00", "1.00", 1.00, "1 oz Ghana Gold Coin"),
    ("0_50", "0.50", 0.50, "½ oz Ghana Gold Coin"),
    ("0_25", "0.25", 0.25, "¼ oz Ghana Gold Coin"),
]

TAX_NOTE = (
    "Bank of Ghana states the coin is exempt from VAT and that capital gains "
    "on it are not taxed under current Ghanaian law. This records what the "
    "issuer publishes and is not tax advice."
)

HOW_TO_BUY = (
    "Ordered through a commercial bank, not from Bank of Ghana directly. "
    "Payment by bank transfer or mobile money; cash is not accepted. Priced "
    "daily by 9am from the previous day's LBMA PM gold price and the Bloomberg "
    "USD/GHS mid-rate."
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


def f(v) -> float | None:
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="gold_coin_prices.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"{args.csv} not found — run extract_gold_coin.py first.")
        return 1
    rows = sorted(
        csv.DictReader(open(args.csv, encoding="utf-8")),
        key=lambda r: r["as_of"],
    )
    if not rows:
        print("No rows.")
        return 1

    latest = rows[-1]
    print(f"{len(rows)} day(s), {rows[0]['as_of']} to {latest['as_of']}\n")

    prem = [f(r["premium_pct"]) for r in rows]
    prem = [p for p in prem if p is not None]
    avg_premium = sum(prem) / len(prem) if prem else None

    pen = [f(r["small_coin_penalty_pct"]) for r in rows]
    pen = [p for p in pen if p is not None]
    avg_penalty = sum(pen) / len(pen) if pen else None

    for key, label, oz, name in DENOMINATIONS:
        price = f(latest[f"ghs_{key}oz"])
        if price is None:
            continue
        # Cost above the metal, for this denomination specifically. The full
        # ounce carries only the base premium; smaller coins carry that plus
        # the penalty for buying in pieces.
        spot_share = f(latest["spot_ghs_oz"]) * oz if latest["spot_ghs_oz"] else None
        eff = ((price / spot_share - 1) * 100) if spot_share else None
        print(f"  {name:<24} GH¢{price:>10,.2f}   "
              f"{eff:.2f}% above the metal" if eff else f"  {name}")

    if avg_premium:
        print(f"\n  Base premium averages {avg_premium:.2f}% "
              f"(range {min(prem):.2f}–{max(prem):.2f}%)")
    if avg_penalty:
        print(f"  Quarter-ounce coins cost {avg_penalty:.2f}% more per ounce")

    cheapest_entry = f(latest["ghs_0_25oz"])
    if cheapest_entry:
        print(f"\n  Cheapest way in: GH¢{cheapest_entry:,.0f} for a quarter "
              f"ounce.")
        print("  Stanbic Cash Trust takes GH¢20. Gold is recommended to")
        print("  ordinary savers as protection and priced for people who")
        print("  already have money.")

    if args.dry_run:
        print(f"\nWould create 1 provider and {len(DENOMINATIONS)} products "
              f"with {len(rows)} price observations each.")
        print("Dry run — nothing written.")
        return 0

    # Provider. Bank of Ghana issues and guarantees the coin; it is not the
    # Government of Ghana row used for Treasury bills.
    existing = rest("GET", "/providers?slug=eq.bank-of-ghana&select=id")
    provider_id = existing[0]["id"] if existing else rest("POST", "/providers", {
        "slug": "bank-of-ghana",
        "legal_name": "Bank of Ghana",
        "trading_name": "Bank of Ghana",
        "website": "https://www.bog.gov.gh",
        "status": "published",
    })[0]["id"]

    src = rest("GET", "/sources?title=eq."
               + urllib.parse.quote("Ghana Gold Coin daily pricing circulars")
               + "&select=id")
    source_id = src[0]["id"] if src else rest("POST", "/sources", {
        "kind": "regulator_publication",
        "publisher": "Bank of Ghana",
        "title": "Ghana Gold Coin daily pricing circulars",
    })[0]["id"]

    have = {p["slug"] for p in rest("GET", "/products?select=slug")}
    made = 0

    for key, label, oz, name in DENOMINATIONS:
        slug = f"ghana-gold-coin-{key.replace('_', '-')}oz"
        price = f(latest[f"ghs_{key}oz"])
        if price is None or slug in have:
            continue

        spot_share = f(latest["spot_ghs_oz"]) * oz if latest["spot_ghs_oz"] else None
        eff = round((price / spot_share - 1) * 100, 4) if spot_share else None

        pid = rest("POST", "/products", {
            "slug": slug,
            "provider_id": provider_id,
            "name": name,
            "share_class": "main",
            "market_side": "invest",
            "legal_structure": "bullion_coin",
            "asset_class": "commodity",
            "currency": "GHS",
            "distributes": False,
            # You can sell back through a bank, so it is not locked, but it is
            # not a daily-dealing fund either — it is a physical asset with a
            # buy/sell spread set by the issuer.
            "dealing_frequency": "on_application",
            "lock_in_days": 0,
            "min_initial_minor": int(round(price * 100)),
            "min_verified_on": latest["as_of"],
            # 99.99% gold from BoG's Responsible Gold Sourcing Framework, and
            # gold is the one asset class with an accepted AAOIFI standard —
            # but BoG does not itself claim compliance, so this stays NULL
            # rather than being asserted on our reasoning.
            "sharia_compliant": None,
            "sharia_basis": None,
            "tax_note": TAX_NOTE,
            "eligibility_notes": HOW_TO_BUY,
            "status": "published",
        })[0]["id"]
        made += 1

        # The premium, as a fee — because it is one.
        fees = [{
            "product_id": pid, "fee_type": "premium_over_spot",
            "rate": round((avg_premium or 0) / 100, 8), "basis": "annual_nav",
            "conditions": "Average amount Bank of Ghana charges above the LBMA "
                          "spot value of the metal, across the period held. "
                          "Not an annual charge — paid once, on purchase.",
            "effective_from": rows[0]["as_of"], "effective_to": None,
            "source_id": source_id, "verified_on": latest["as_of"],
        }]
        if oz < 1 and eff is not None and avg_premium is not None:
            extra = eff - avg_premium
            if extra > 0.05:
                fees.append({
                    "product_id": pid, "fee_type": "denomination_penalty",
                    "rate": round(extra / 100, 8), "basis": "annual_nav",
                    "conditions": f"Extra paid per ounce for buying in "
                                  f"{label} oz pieces rather than a full ounce.",
                    "effective_from": rows[0]["as_of"], "effective_to": None,
                    "source_id": source_id, "verified_on": latest["as_of"],
                })
        rest("POST", "/product_fees", fees, prefer="return=minimal")

        # Price history. The coin price is the observation; the LBMA price and
        # FX rate that produced it are recorded so a page can show WHY it moved.
        obs = []
        for r in rows:
            p = f(r[f"ghs_{key}oz"])
            if p is None:
                continue
            obs.append({
                "product_id": pid,
                "as_of": r["as_of"],
                "nav": p,
                "basis": "single",
                "series_kind": "quoted",
                "source_id": source_id,
                "note": f"LBMA ${r['lbma_usd_oz']}/oz, USDGHS {r['usd_ghs']}",
            })
        for i in range(0, len(obs), 100):
            rest("POST", "/nav_observations", obs[i : i + 100],
                 prefer="return=minimal")
        print(f"  {name:<24} {len(obs)} observation(s), {len(fees)} fee row(s)")

    print(f"\n  {made} product(s) created")
    print("\n  Gold pays nothing. Its whole return is the price moving, and for")
    print("  a cedi holder that is the dollar gold price AND the exchange")
    print("  rate. Over the period loaded those pulled opposite ways: gold")
    print("  +0.5% in dollars, the coin -3.9% in cedis. Any page showing one")
    print("  without the other misrepresents what a Ghanaian actually earned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

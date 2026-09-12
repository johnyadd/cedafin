"""
load_gse.py — listed equities and broker market share into the database.

TWO LOADS, TWO PURPOSES

  EQUITIES become products, so a share sits on the same page as a fund, a
  Treasury bill and a gold coin. NewGold ETF matters most: about GH¢462 a unit
  against GH¢13,803 for the cheapest Ghana Gold Coin. Same metal, thirty times
  cheaper to start, which for most Ghanaian savers is the difference between
  possible and not.

  BROKERS become providers with market share attached. Not because share is a
  quality measure — it is not — but because Ghanaian brokers publish no
  commission rates at all, so it is the only comparable public fact about them.

WHAT THE BROKER SERIES ACTUALLY SHOWS
IC Securities' share of value traded, month by month:

    68.08  48.98  66.52  42.30  19.97  66.19  44.57  32.65
    23.40  56.58  76.86  50.28  64.14  51.09  78.82

That is not a firm consolidating power. It swings thirty points in a month
with no direction, which means a few block trades decide who leads — the
market is thin enough that monthly totals are set by a handful of
transactions. Reporting the latest figure alone would imply a dominance that
the series flatly contradicts, so the whole series is stored and the page must
show the range rather than the last number.

The same thinness appears in the headline figures: the index rose 76% in the
year to July 2026 while volume fell 72%. Prices moving hard on very little
trading. For a saver that is the warning — a 76% gain in a market this thin is
not necessarily a gain you can realise.

EQUITIES ARE PRICES, NOT CHARGES
A share has no management fee. What it costs is brokerage, and nobody
publishes that. So equity products carry no charge figure and say so, rather
than showing a zero that would imply free.

Usage:
    python load_gse.py --dry-run
    python load_gse.py
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

# Only instruments a retail saver could reasonably compare with a fund. The
# report also carries indices and totals, which are not investable.
SKIP_TICKERS = {"TOTALS", "TOTAL", "GSE", "GSECI", "GSEFSI"}

# The one ETF on the exchange, and the reason this loader exists.
ETF_TICKERS = {"GLD"}


def env() -> dict:
    """
    Credentials from .env.local locally, from the environment in CI.

    A scheduled run has no .env.local — the file holds a service-role key and
    the repository is public. It has environment variables instead, supplied
    from repository secrets.
    """
    out = {}
    if os.path.exists(".env.local"):
        for line in open(".env.local", encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()

    # Environment wins, so a scheduled run is never affected by a stale file.
    for k in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if os.environ.get(k):
            out[k] = os.environ[k]

    missing = [k for k in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") if not out.get(k)]
    if missing:
        print(f"Missing {chr(44).join(missing)} — not in .env.local or the environment.")
        sys.exit(1)
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


# The exchange renames brokers between reports — adding and dropping
# "Limited", switching "Capital" for "Capital Markets", and misspelling
# "Securities" twice. Slugifying the name as printed produced THIRTY-SEVEN
# provider records for twenty-four firms, with some months counted under one
# name and some under another. Market shares were split and, where the ranges
# overlapped, double-counted.
#
# Nothing flagged it. Each card read correctly on its own; only comparing
# records against each other showed the problem, months after the fact.
GSE_TYPOS = {
    "securties": "securities",
    "securites": "securities",
    "firstatlantic": "first atlantic",
}

# Words the exchange uses inconsistently and which identify nobody. What is
# left after removing them is the firm: Serengeti, Merban, First Atlantic.
BROKER_NOISE = (
    r"\b(limited|ltd|plc|company|co|markets?|capital|securities|brokerage|"
    r"stockbrokers?)\b"
)


# The exchange prints broker names in capitals, so .title() turns IC into
# Ic and NTHC into Nthc. These stay as they are.
ACRONYMS = {"IC", "SBG", "CDH", "EDC", "NTHC", "SIC", "UMB", "ETF"}


def broker_display(name: str) -> str:
    """Title case, except for the acronyms that are not words."""
    return " ".join(
        w.upper() if w.upper() in ACRONYMS else w.title() for w in name.split()
    )


def broker_key(name: str) -> str:
    """A stable identity for a broker, whatever the report called it."""
    s = name.lower()
    for wrong, right in GSE_TYPOS.items():
        s = s.replace(wrong, right)
    s = re.sub(r"[^a-z ]+", " ", s)
    s = re.sub(BROKER_NOISE, " ", s)
    return re.sub(r"\s+", " ", s).strip()

def slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def f(v) -> float | None:
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--equities-csv", default="gse_equities.csv")
    ap.add_argument("--brokers-csv", default="gse_brokers.csv")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--etf-only", action="store_true",
                    help="Load only the ETF, not all 40 listed shares.")
    args = ap.parse_args()

    eq = list(csv.DictReader(open(args.equities_csv, encoding="utf-8"))) \
        if os.path.exists(args.equities_csv) else []
    br = list(csv.DictReader(open(args.brokers_csv, encoding="utf-8"))) \
        if os.path.exists(args.brokers_csv) else []
    if not eq and not br:
        print("Nothing to load — run extract_gse.py first.")
        return 1

    latest_eq = max((r["as_of"] for r in eq), default=None)
    latest_br = max((r["as_of"] for r in br), default=None)

    tickers = sorted({
        r["ticker"] for r in eq
        if r["ticker"] not in SKIP_TICKERS
        and (not args.etf_only or r["ticker"] in ETF_TICKERS)
    })
    # One entry per FIRM, not per spelling. The display name is the most
    # recent spelling; the key is what identifies it.
    by_key: dict[str, str] = {}
    for r in sorted(br, key=lambda x: x.get("as_of", "")):
        by_key[broker_key(r["broker"])] = r["broker"]
    brokers = sorted(by_key.values())

    print(f"{len(eq)} equity rows, {len(br)} broker rows")
    print(f"  latest equities {latest_eq}, latest brokers {latest_br}")
    print(f"  {len(tickers)} ticker(s), {len(brokers)} broker(s)\n")

    # The concentration picture, stated as a range rather than a snapshot.
    if br:
        shares: dict[str, list[float]] = {}
        for r in br:
            v = f(r["value_share_pct"])
            if v is not None:
                # Keyed on the firm, not the printed name — otherwise the
                # summary reports one broker twice under two spellings.
                shares.setdefault(broker_key(r["broker"]).upper(), []).append(v)
        ranked = sorted(
            shares.items(),
            key=lambda kv: -(sum(kv[1]) / len(kv[1])),
        )
        print("  Average share of value traded, over the period:")
        for name, vals in ranked[:5]:
            print(f"    {name[:34]:<36} {sum(vals)/len(vals):>6.2f}%  "
                  f"(ranged {min(vals):.2f}–{max(vals):.2f}%)")
        top = ranked[0]
        print(f"\n  {top[0]} swings {min(top[1]):.2f}% to {max(top[1]):.2f}% "
              f"month to month.")
        print("  A few block trades decide who leads — the market is thin")
        print("  enough that monthly totals turn on a handful of deals.")

    gld = [r for r in eq if r["ticker"] == "GLD"]
    if gld:
        g = sorted(gld, key=lambda x: x["as_of"])[-1]
        print(f"\n  NewGold ETF at {g['as_of']}: GH¢{f(g['closing_vwap']):,.2f} "
              f"a unit, against GH¢13,803 for the cheapest gold coin.")

    if args.dry_run:
        print(f"\nWould create {len(brokers)} broker provider(s) and "
              f"{len(tickers)} equity product(s).")
        print("Dry run — nothing written.")
        return 0

    src = rest("GET", "/sources?title=eq."
               + urllib.parse.quote("GSE monthly equities market reports")
               + "&select=id")
    source_id = src[0]["id"] if src else rest("POST", "/sources", {
        "kind": "regulator_publication",
        "publisher": "Ghana Stock Exchange",
        "title": "GSE monthly equities market reports",
    })[0]["id"]

    # Brokers as providers. Market share goes in the notes rather than as a
    # score — it measures activity, not quality, and a page that ranked on it
    # would be telling savers something it cannot support.
    # Keyed on the FIRM, not the slug. Matching on slug meant a record
    # created under an older spelling was never found, so every run added a
    # rival rather than updating — twice, before a unique index on the
    # normalised name made it impossible.
    #
    # That index is the real fix. This lookup just means the loader updates
    # cleanly instead of being rejected.
    existing = {}
    for p in rest("GET", "/providers?select=id,slug,trading_name"):
        if p["slug"].startswith("broker-"):
            existing[broker_key(p.get("trading_name") or p["slug"])] = p["id"]
        existing[p["slug"]] = p["id"]
    made_b = 0
    for name in brokers:
        # Keyed on the firm rather than the printed name, so a rename in
        # next month's report updates the record instead of creating a rival.
        slug = "broker-" + slugify(broker_key(name))
        if broker_key(name) in existing or slug in existing:
            continue
        key = broker_key(name)
        vals = [
            f(r["value_share_pct"]) for r in br if broker_key(r["broker"]) == key
        ]
        vals = [v for v in vals if v is not None]
        avg = sum(vals) / len(vals) if vals else 0
        rest("POST", "/providers", {
            "slug": slug,
            "legal_name": broker_display(name),
            "trading_name": broker_display(name),
            "status": "draft",
            "notes": (
                f"Licensed dealing member of the Ghana Stock Exchange. "
                f"Averaged {avg:.2f}% of value traded across "
                f"{len(vals)} monthly reports, ranging "
                f"{min(vals):.2f}%–{max(vals):.2f}%. Share measures activity, "
                f"not quality or cost — no Ghanaian broker publishes its "
                f"commission rates."
            ) if vals else "Licensed dealing member of the Ghana Stock Exchange.",
        })
        made_b += 1

    # Equities. One provider for the exchange itself, since a listed company
    # is not a "provider" in the sense the rest of this database uses.
    gse_id = existing.get("ghana-stock-exchange") or rest("POST", "/providers", {
        "slug": "ghana-stock-exchange",
        "legal_name": "Ghana Stock Exchange",
        "trading_name": "Ghana Stock Exchange",
        "website": "https://gse.com.gh",
        "status": "published",
    })[0]["id"]

    have = {p["slug"] for p in rest("GET", "/products?select=slug")}
    made_p = 0
    for ticker in tickers:
        rows = sorted([r for r in eq if r["ticker"] == ticker],
                      key=lambda x: x["as_of"])
        if not rows:
            continue
        last = rows[-1]
        slug = f"gse-{slugify(ticker)}"
        if slug in have:
            continue

        is_etf = ticker in ETF_TICKERS
        pid = rest("POST", "/products", {
            "slug": slug,
            "provider_id": gse_id,
            "name": f"{ticker} ({last['sector'] or 'Listed'})" if not is_etf
                    else "NewGold ETF",
            "share_class": "main",
            "market_side": "invest",
            "legal_structure": "etf" if is_etf else "other",
            "asset_class": "commodity" if is_etf else "equity",
            "currency": "GHS",
            "distributes": True,
            "dealing_frequency": "daily",
            "lock_in_days": 0,
            "min_initial_minor": int(round((f(last["closing_vwap"]) or 0) * 100)),
            "min_verified_on": last["as_of"],
            # Sharia compliance is claimed by NewGold's own documentation.
            "sharia_compliant": True if is_etf else None,
            "sharia_basis": ("NewGold ETF is described by its issuer as a "
                             "Shariah-compliant fund, launched by Absa Capital "
                             "and backed by physical bullion.") if is_etf else None,
            # No management charge on a share, and brokerage is unpublished —
            # so nothing is claimed rather than a zero that implies free.
            "eligibility_notes": (
                "Bought through a licensed dealing member of the Ghana Stock "
                "Exchange. Brokerage is charged on top and no Ghanaian broker "
                "publishes its rates, so the cost of buying this is not shown."
            ),
            "status": "published",
        })[0]["id"]
        made_p += 1

        obs = [{
            "product_id": pid,
            "as_of": r["as_of"],
            "nav": f(r["closing_vwap"]),
            "basis": "single",
            "series_kind": "quoted",
            "source_id": source_id,
        } for r in rows if f(r["closing_vwap"]) is not None]
        for i in range(0, len(obs), 100):
            rest("POST", "/nav_observations", obs[i : i + 100],
                 prefer="return=minimal")

    print(f"\n  {made_b} broker provider(s), {made_p} equity product(s) created")
    print("\n  Brokers are loaded as DRAFT. Market share says who is busy, not")
    print("  who is good or cheap, and until one publishes a commission rate")
    print("  there is nothing to compare them on.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

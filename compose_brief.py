"""
compose_brief.py — what changed, and nothing else.

WHAT THE SUBSCRIBE FORM PROMISES
"When the numbers move, what moved and where it came from." That promise was
made on the strength of the scheduled fetchers: gold daily, Treasury bills
weekly, the exchange and the registers monthly. We know when something moves.

What we did not have was anything that says WHICH thing moved. A figure in the
database is the current value; it carries no memory of what it replaced.

So this takes a snapshot each time it runs and diffs against the last one.
The first run has nothing to compare against and says so.

THE RULE THAT MATTERS MOST
If nothing moved, do not send. A note saying "nothing changed this month" is
the fastest way to teach somebody to ignore the next one — and the next one
might be the month a fund doubled its fee.

WHY IT DOES NOT SEND
Deliberately separate. This composes and prints; sending is a different
concern with its own failure modes and its own API key. Running this by hand
each month costs a minute and proves whether there is anything worth saying
before anybody builds a sender.

The list currently holds one address, which is the author's, from testing the
form. There is time to get this right.

Usage:
    python compose_brief.py              # compose and show, snapshot nothing
    python compose_brief.py --snapshot   # compose and record for next time
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date


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
        print(f"  {e.read().decode('utf-8', 'replace')[:300]}\n")
        raise


def current() -> dict:
    """The headline figures as they stand, in one flat dict for diffing."""
    out: dict[str, float | str | None] = {}

    # Treasury bills, by tenor. The benchmark everything else is read against.
    tb = call(
        "GET",
        "/products?asset_class=eq.government_security&status=eq.published"
        "&select=name,nav_observations(as_of,yield_annualised)",
    )
    for p in tb or []:
        obs = [
            o
            for o in (p.get("nav_observations") or [])
            if o.get("yield_annualised") is not None
        ]
        if not obs:
            continue
        latest = max(obs, key=lambda o: o["as_of"])
        for days in (91, 182, 364):
            if str(days) in str(p.get("name", "")):
                out[f"tbill_{days}"] = round(latest["yield_annualised"] * 100, 2)
                out[f"tbill_{days}_as_of"] = latest["as_of"]

    infl = call(
        "GET",
        "/macro_series?series_code=eq.GH_CPI_YOY&select=value,as_of"
        "&order=as_of.desc&limit=1",
    )
    if infl:
        out["inflation"] = round(float(infl[0]["value"]) * 100, 2)
        out["inflation_as_of"] = infl[0]["as_of"]

    # SME lending range. The figure this site is known for.
    sme = call(
        "GET",
        "/products?market_side=eq.borrow&asset_class=eq.sme_credit"
        "&lock_in_days=eq.365&rate_max=not.is.null"
        "&select=rate_max,providers(trading_name)&order=rate_max.asc",
    )
    if sme:
        out["sme_min"] = round(float(sme[0]["rate_max"]) * 100, 2)
        out["sme_max"] = round(float(sme[-1]["rate_max"]) * 100, 2)
        out["sme_cheapest"] = (sme[0].get("providers") or {}).get("trading_name")
        out["sme_dearest"] = (sme[-1].get("providers") or {}).get("trading_name")

    # Fund charges, one entry per fund that publishes one. A change here is
    # the most interesting thing that can happen in a month.
    fees = call(
        "GET",
        "/product_fees?fee_type=eq.stated_charges&rate=not.is.null"
        "&select=rate,products(name,status)",
    )
    for f in fees or []:
        prod = f.get("products") or {}
        if prod.get("status") != "published":
            continue
        out[f"fee::{prod.get('name')}"] = round(float(f["rate"]) * 100, 2)

    # How many providers publish anything, per field. Movement here is the
    # outreach working.
    disc = call("GET", "/provider_disclosure?select=field,published_on")
    counts: dict[str, int] = {}
    for r in disc or []:
        if r.get("published_on"):
            counts[r["field"]] = counts.get(r["field"], 0) + 1
    for field, n in counts.items():
        out[f"publish::{field}"] = n

    return out


def describe(key: str, old, new) -> str | None:
    """One line for a change, or None where the change is not worth a line."""
    if key.endswith("_as_of"):
        return None

    if key.startswith("fee::"):
        name = key.split("::", 1)[1]
        if old is None:
            return f"{name} published a charge for the first time: {new}% a year."
        direction = "cut" if new < old else "raised"
        return f"{name} {direction} its charge from {old}% to {new}% a year."

    if key.startswith("publish::"):
        field = key.split("::", 1)[1].replace("_", " ")
        if old is None:
            return None
        if new > old:
            return (
                f"{new - old} more provider(s) now publish {field} — "
                f"{new} in total."
            )
        return None

    labels = {
        "tbill_91": "The 91-day Treasury bill",
        "tbill_182": "The 182-day Treasury bill",
        "tbill_364": "The 364-day Treasury bill",
        "inflation": "Inflation",
        "sme_min": "The cheapest one-year SME loan",
        "sme_max": "The dearest one-year SME loan",
    }
    if key in labels and isinstance(new, (int, float)) and isinstance(old, (int, float)):
        if abs(new - old) < 0.005:
            return None
        direction = "fell" if new < old else "rose"
        return f"{labels[key]} {direction} from {old}% to {new}%."

    if key in ("sme_cheapest", "sme_dearest") and old != new:
        which = "cheapest" if key == "sme_cheapest" else "dearest"
        return f"The {which} bank changed from {old} to {new}."

    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    args = ap.parse_args()

    now = current()
    prev = call(
        "GET", "/brief_snapshot?select=taken_on,figures&order=taken_on.desc&limit=1"
    )

    print()
    if not prev:
        print("  No previous snapshot — nothing to compare against.")
        print()
        print("  Current figures:")
        for k, v in sorted(now.items()):
            if not k.endswith("_as_of"):
                print(f"    {k:<42} {v}")
        print()
        print("  Run with --snapshot to record these. Next month's run will")
        print("  diff against them and produce a note.")
        if args.snapshot:
            call(
                "POST",
                "/brief_snapshot",
                {"taken_on": date.today().isoformat(), "figures": now},
            )
            print()
            print("  Snapshot recorded.")
        return 0

    old = prev[0]["figures"]
    since = prev[0]["taken_on"]

    lines = []
    for key in sorted(set(now) | set(old)):
        line = describe(key, old.get(key), now.get(key))
        if line:
            lines.append(line)

    print(f"  Changes since {since}")
    print()
    if not lines:
        print("  Nothing moved.")
        print()
        print("  Do not send. A note saying nothing changed is how a reader")
        print("  learns to ignore the one that matters.")
    else:
        for line in lines:
            print(f"    {line}")
        print()
        print(f"  {len(lines)} change(s) — worth sending.")

    if args.snapshot:
        call(
            "POST",
            "/brief_snapshot",
            {"taken_on": date.today().isoformat(), "figures": now},
        )
        print()
        print("  Snapshot recorded for next time.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
load_broker_activity.py — broker market share as figures, and publish them.

WHAT CHANGES
The GSE load created 24 broker providers as drafts with their share written
into notes as a sentence. This puts the same facts into columns so a page can
sort and compare them, and flips them to published.

WHY THEY WERE DRAFT, AND WHY THAT WAS TOO STRICT
The original reasoning: market share says who is busy, not who is good or
cheap, and no Ghanaian broker publishes a commission rate — so there was
nothing honest to compare them on.

But that withheld the only public data on Ghanaian stockbrokers that exists.
Fifteen months of it, from the exchange itself. A saver choosing where to open
an account currently has nothing at all; showing activity with a clear
statement of what it does and does not mean is better than showing nothing and
calling it caution.

WHAT THE PAGE MUST SAY WITH THESE NUMBERS
Three things, and the loader records the data to support each:

  The range, not just the average. IC Securities runs 19.97% to 78.82% across
  the period. The high figure alone implies a captured market; the average
  alone implies comfortable leadership. Neither is true — a few block trades
  decide who leads in any given month, which is a fact about how thin the
  exchange is rather than about any firm.

  Months observed. A broker appearing in three reports is not comparable with
  one appearing in fifteen, and averaging both without saying so would flatter
  the occasional participant.

  That none of this is cost. Twenty-four licensed dealing members, not one
  published commission rate.

Usage:
    python load_broker_activity.py --dry-run
    python load_broker_activity.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request


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


def slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="gse_brokers.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"{args.csv} not found — run extract_gse.py first.")
        return 1

    rows = list(csv.DictReader(open(args.csv, encoding="utf-8")))
    if not rows:
        print("No rows.")
        return 1

    # A broker can appear twice in one month under two spellings. Those were
    # merged by name, but their shares must be ADDED within a month, not
    # averaged, or a merged firm's share is halved.
    by_month: dict[tuple[str, str], float] = {}
    for r in rows:
        try:
            v = float(r["value_share_pct"])
        except (TypeError, ValueError):
            continue
        key = (r["broker"], r["as_of"])
        by_month[key] = by_month.get(key, 0.0) + v

    stats: dict[str, dict] = {}
    for (broker, as_of), v in by_month.items():
        s = stats.setdefault(broker, {"vals": [], "dates": []})
        s["vals"].append(v)
        s["dates"].append(as_of)

    ranked = sorted(
        stats.items(),
        key=lambda kv: -(sum(kv[1]["vals"]) / len(kv[1]["vals"])),
    )

    print(f"{len(ranked)} broker(s) across "
          f"{len({d for s in stats.values() for d in s['dates']})} month(s)\n")
    for name, s in ranked:
        vals = s["vals"]
        avg = sum(vals) / len(vals)
        print(f"  {name[:34]:<36} {avg:>6.2f}%  "
              f"({min(vals):>5.2f}–{max(vals):>5.2f}%)  "
              f"{len(vals):>2} month(s)")

    top = ranked[0]
    tvals = top[1]["vals"]
    print(f"\n  {top[0]} averages {sum(tvals)/len(tvals):.2f}% but ranges "
          f"{min(tvals):.2f}% to {max(tvals):.2f}%.")
    print("  A fifty-point swing with no direction is a fact about how thin")
    print("  the exchange is, not about how dominant any firm is.")

    if args.dry_run:
        print("\nDry run — nothing written.")
        return 0

    updated = 0
    for name, s in ranked:
        slug = "broker-" + slugify(name)
        vals, dates = s["vals"], sorted(s["dates"])
        try:
            rest("PATCH", f"/providers?slug=eq.{slug}", {
                "broker_share_avg_pct": round(sum(vals) / len(vals), 2),
                "broker_share_min_pct": round(min(vals), 2),
                "broker_share_max_pct": round(max(vals), 2),
                "broker_months_observed": len(vals),
                "broker_first_seen": dates[0],
                "broker_last_seen": dates[-1],
                "status": "published",
            }, prefer="return=minimal")
            updated += 1
        except RuntimeError as e:
            print(f"    {slug}: {str(e)[:120]}")
            break

    print(f"\n  {updated} broker(s) updated and published")
    print("\n  These figures are ACTIVITY. Not cost, not quality, not a")
    print("  recommendation. Twenty-four licensed dealing members and not one")
    print("  published commission rate — which is the gap, and the ask.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

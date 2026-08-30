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
    vol_month: dict[tuple[str, str], float] = {}
    # Absolute figures for the most recent month, so a percentage can be read
    # against the size of the market it is a share of.
    latest = max(r["as_of"] for r in rows)
    abs_latest: dict[str, dict] = {}

    for r in rows:
        key = (r["broker"], r["as_of"])
        try:
            by_month[key] = by_month.get(key, 0.0) + float(r["value_share_pct"])
        except (TypeError, ValueError):
            pass
        try:
            vol_month[key] = vol_month.get(key, 0.0) + float(r["volume_share_pct"])
        except (TypeError, ValueError):
            pass
        if r["as_of"] == latest:
            a = abs_latest.setdefault(r["broker"], {"value": 0.0, "volume": 0.0})
            try:
                a["value"] += float(r["value_traded_ghs"])
            except (TypeError, ValueError):
                pass
            try:
                a["volume"] += float(r["volume_traded"])
            except (TypeError, ValueError):
                pass

    stats: dict[str, dict] = {}
    for (broker, as_of), v in by_month.items():
        s = stats.setdefault(broker, {"vals": [], "dates": [], "vols": []})
        s["vals"].append(v)
        s["dates"].append(as_of)
    for (broker, _), v in vol_month.items():
        stats.setdefault(broker, {"vals": [], "dates": [], "vols": []})
        stats[broker].setdefault("vols", []).append(v)

    ranked = sorted(
        stats.items(),
        key=lambda kv: -(sum(kv[1]["vals"]) / len(kv[1]["vals"])),
    )

    print(f"{len(ranked)} broker(s) across "
          f"{len({d for s in stats.values() for d in s['dates']})} month(s)\n")
    for name, s in ranked:
        vals = s["vals"]
        vols = s.get("vols") or []
        avg = sum(vals) / len(vals)
        vavg = sum(vols) / len(vols) if vols else None
        # Value above volume means fewer, larger trades — the closest this
        # data comes to saying whether a firm handles retail business.
        tilt = ""
        if vavg is not None and vavg > 0:
            if avg > vavg * 1.15:
                tilt = "  larger trades"
            elif vavg > avg * 1.15:
                tilt = "  smaller trades"
        print(f"  {name[:30]:<32} value {avg:>6.2f}%  "
              f"volume {vavg:>6.2f}%" if vavg is not None
              else f"  {name[:30]:<32} value {avg:>6.2f}%  volume      —")
        if tilt:
            print(f"      {tilt.strip()}")

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
            vols = s.get("vols") or []
            ab = abs_latest.get(name, {})
            rest("PATCH", f"/providers?slug=eq.{slug}", {
                "broker_volume_share_avg_pct":
                    round(sum(vols) / len(vols), 2) if vols else None,
                "broker_value_traded_ghs":
                    round(ab["value"], 2) if ab.get("value") else None,
                "broker_volume_traded":
                    int(ab["volume"]) if ab.get("volume") else None,
                "broker_latest_month": latest,
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

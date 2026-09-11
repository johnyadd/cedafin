"""
consolidate_brokers.py — sixty-one records for twenty-four firms.

HOW THIS HAPPENED
The Ghana Stock Exchange renames brokers between monthly reports. It adds and
drops "Limited", switches "Capital" for "Capital Markets", and has misspelled
"Securities" twice — Securties and Securites. The loader slugified the name as
printed, so every variant became a separate provider.

Thirty-seven records for twenty-four firms, with each firm's months split
across its spellings. Where the date ranges overlapped, months were counted
twice. Market shares were wrong in both directions and nothing flagged it,
because every card read correctly on its own.

Then the fix made it briefly worse: the corrected loader created twenty-four
NEW records under normalised slugs, leaving sixty-one in total — the new ones
empty of contact details, the old ones holding them.

WHAT THIS DOES
For each firm, keyed on the normalised name:

  Picks the canonical record — the one carrying the most contact and access
  detail, because those were entered by hand and cannot be regenerated. A
  market share can be recomputed from the CSV; an email address that took a
  bounced message and a correction to establish cannot.

  Recomputes market share from gse_brokers.csv rather than averaging the
  averages. Averaging an average across different month counts is wrong, and
  it is the mistake I made merging Databank by hand an hour ago.

  Carries across anything the canonical record lacks and a duplicate has.

  Deletes the rest, after checking nothing references them.

WHY IT RECOMPUTES RATHER THAN MERGES
The provider columns are derived. The CSV is the source. Deriving twice from
the source gives the same answer; merging derived values does not.

Usage:
    python consolidate_brokers.py --dry-run
    python consolidate_brokers.py
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
from collections import defaultdict

BROKERS_CSV = "gse_brokers.csv"

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
    s = name.lower()
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
        print(f"  {e.read().decode('utf-8', 'replace')[:400]}\n")
        raise


# Fields entered by hand or established by correspondence. These are the
# reason we merge rather than delete-and-reload: a bounced address that took
# three attempts to correct is not recoverable from a CSV.
CARRY = [
    "website",
    "contact_email",
    "contact_phone",
    "office_address",
    "legal_name",
    "notes",
    "access_requirements",
    "access_verified_on",
    "offers_custody",
]


def completeness(p: dict) -> int:
    """How much hand-entered detail a record carries."""
    return sum(1 for f in CARRY if p.get(f) not in (None, "", False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(BROKERS_CSV):
        print(f"  {BROKERS_CSV} not found — run extract_gse.py first.")
        return 1

    rows = list(csv.DictReader(open(BROKERS_CSV, encoding="utf-8")))
    # Market share recomputed from source, grouped by firm.
    shares: dict[str, list[float]] = defaultdict(list)
    months: dict[str, set[str]] = defaultdict(set)
    volumes: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        k = broker_key(r["broker"])
        try:
            v = float(r["value_share_pct"])
            shares[k].append(v)
            months[k].add(r.get("as_of", ""))
        except (TypeError, ValueError):
            pass
        try:
            volumes[k].append(float(r.get("volume_share_pct") or ""))
        except (TypeError, ValueError):
            pass

    providers = call(
        "GET", "/providers?slug=like.broker-*&select=*&order=slug.asc"
    )
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in providers:
        groups[broker_key(p.get("trading_name") or p["slug"])].append(p)

    print(f"  {len(providers)} records -> {len(groups)} firms")
    print()

    plan = []
    for key, members in sorted(groups.items()):
        # The record with the most hand-entered detail wins. Ties break on the
        # normalised slug, which is what the corrected loader will write to.
        members.sort(
            key=lambda p: (completeness(p), p["slug"] == f"broker-{key.replace(' ', '-')}"),
            reverse=True,
        )
        keeper = members[0]
        losers = members[1:]

        merged = {}
        for f in CARRY:
            if keeper.get(f) in (None, "", False):
                for other in losers:
                    if other.get(f) not in (None, "", False):
                        merged[f] = other[f]
                        break

        vals = shares.get(key, [])
        vols = [v for v in volumes.get(key, []) if v is not None]
        if vals:
            merged["broker_share_avg_pct"] = sum(vals) / len(vals)
            merged["broker_share_min_pct"] = min(vals)
            merged["broker_share_max_pct"] = max(vals)
            merged["broker_months_observed"] = len(months.get(key, set()))
            # The month COUNT came from the CSV and the date RANGE did not, so
            # a merged firm showed "15 months (Feb 2026 - Jul 2026)". Both now
            # derive from the same set.
            seen = sorted(d for d in months.get(key, set()) if d)
            if seen:
                merged["broker_first_seen"] = seen[0]
                merged["broker_last_seen"] = seen[-1]
        if vols:
            merged["broker_volume_share_avg_pct"] = sum(vols) / len(vols)

        plan.append((key, keeper, losers, merged, len(vals)))

    for key, keeper, losers, merged, n in plan:
        share = merged.get("broker_share_avg_pct")
        print(
            f"  {key[:20]:<22} keep {keeper['slug'][:38]:<40} "
            f"{('%.2f%%' % share) if share is not None else '—':>8}  "
            f"{n:>2}mo  drop {len(losers)}"
        )
        for other in losers:
            print(f"      drop {other['slug']}")

    if args.dry_run:
        print()
        print(f"  Would keep {len(plan)}, delete {sum(len(l) for _, _, l, _, _ in plan)}.")
        print("  Dry run — nothing written.")
        return 0

    print()
    kept = dropped = 0
    for key, keeper, losers, merged, _ in plan:
        if merged:
            call("PATCH", f"/providers?id=eq.{keeper['id']}", merged)
        kept += 1

        for other in losers:
            # Never delete a record something else points at. A broker with
            # products attached would orphan them silently — the same class of
            # failure as the duplicates themselves.
            refs = call(
                "GET", f"/products?provider_id=eq.{other['id']}&select=id"
            )
            if refs:
                print(f"    {other['slug']} has {len(refs)} product(s) — kept")
                continue
            call("DELETE", f"/providers?id=eq.{other['id']}")
            dropped += 1

    print(f"  {kept} firms kept, {dropped} duplicate record(s) deleted")
    print()
    print("  Market share recomputed from the CSV, not merged from the")
    print("  provider rows — averaging averages across different month")
    print("  counts is how the first attempt at this went wrong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

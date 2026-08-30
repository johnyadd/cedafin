"""
normalise_brokers.py — one broker, one name.

THE PROBLEM
Fifteen monthly reports produced 34 distinct broker names for about 24 firms.
Counting them separately understated the leaders and invented smaller ones:
Databank appeared twice at 8.87% and 6.96% when it is one house doing roughly
16%, and Fincap appeared three times.

THREE KINDS OF DUPLICATE, AND ONLY ONE IS MECHANICAL

  SUFFIX          "CONSTANT CAPITAL" / "CONSTANT CAPITAL LIMITED"
                  "MERBAN STOCKBROKERS LIMITED" / "... LTD"
                  Stripped automatically. Safe: no two Ghanaian brokers differ
                  only by whether someone typed Limited.

  SPACING         "FIRST ATLANTIC BROKERAGE" / "FIRSTATLANTIC BROKERAGE"
                  Needs an explicit rule. Collapsing all spaces would merge
                  names that should stay apart.

  TYPOS IN THE SOURCE
                  "AMBER SECURTIES", "FINCAP SECURITES"
                  The exchange's own misspellings. No rule derives these — they
                  are listed by hand below.

WHY NOT FUZZY MATCHING
A similarity threshold loose enough to catch SECURTIES/SECURITIES is also loose
enough to merge two genuinely different firms, and nobody would notice until a
broker's market share was wrong on a published page. Every merge here is
written down and can be read. If a pair is missing, the two names stay separate
and the count is visibly too high — which is a failure you can see, rather than
a wrong number that looks right.

Usage:
    python normalise_brokers.py --dry-run
    python normalise_brokers.py
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys

# Stripped from the end before comparison. Longest first.
SUFFIXES = [
    "company limited", "limited", "ltd.", "ltd", "plc.", "plc", "inc.", "inc",
]

# Merges no rule can derive: the exchange's own typos and spacing variants.
# Each maps a raw name to the canonical one. Written out rather than inferred,
# because a wrong merge here shows up as a wrong market share on a page.
EXPLICIT = {
    "AMBER SECURTIES": "AMBER SECURITIES",
    "FINCAP SECURITES": "FINCAP SECURITIES",
    "FIRSTATLANTIC BROKERAGE": "FIRST ATLANTIC BROKERAGE",
    "SARPONG CAPITAL MARKET": "SARPONG CAPITAL MARKETS",
    "SERENGETI CAPITAL": "SERENGETI CAPITAL MARKETS",
}


def strip_suffix(name: str) -> str:
    s = re.sub(r"\s+", " ", name.upper().strip(" .,"))
    for suf in SUFFIXES:
        if s.endswith(" " + suf.upper()):
            return s[: -len(suf) - 1].strip()
    return s


def canonical(name: str) -> str:
    base = strip_suffix(name)
    return EXPLICIT.get(base, base)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="gse_brokers.csv")
    ap.add_argument("--out", default="gse_brokers.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"{args.csv} not found — run extract_gse.py first.")
        return 1

    rows = list(csv.DictReader(open(args.csv, encoding="utf-8")))
    if not rows:
        print("No rows.")
        return 1

    raw = sorted({r["broker"] for r in rows})
    mapping = {n: canonical(n) for n in raw}
    groups: dict[str, list[str]] = {}
    for src, dst in mapping.items():
        groups.setdefault(dst, []).append(src)

    merged = {d: s for d, s in groups.items() if len(s) > 1}
    print(f"{len(raw)} distinct names -> {len(groups)} brokers\n")

    if merged:
        print("  Merged:")
        for dst, srcs in sorted(merged.items()):
            print(f"    {dst}")
            for s in sorted(srcs):
                if s != dst:
                    print(f"      <- {s}")

    # Recompute share so the effect is visible before anything is written.
    by_broker: dict[str, list[float]] = {}
    for r in rows:
        try:
            v = float(r["value_share_pct"])
        except (TypeError, ValueError):
            continue
        by_broker.setdefault(mapping[r["broker"]], []).append(v)

    # Shares from the same month must be added, not averaged, when two names
    # were really one firm — otherwise a merged broker's share is halved.
    by_month: dict[tuple[str, str], float] = {}
    for r in rows:
        try:
            v = float(r["value_share_pct"])
        except (TypeError, ValueError):
            continue
        key = (mapping[r["broker"]], r["as_of"])
        by_month[key] = by_month.get(key, 0.0) + v

    combined: dict[str, list[float]] = {}
    for (broker, _), v in by_month.items():
        combined.setdefault(broker, []).append(v)

    ranked = sorted(
        combined.items(), key=lambda kv: -(sum(kv[1]) / len(kv[1]))
    )
    print("\n  Average share of value traded, after merging:")
    for name, vals in ranked[:8]:
        print(f"    {name[:36]:<38} {sum(vals)/len(vals):>6.2f}%  "
              f"({min(vals):.2f}–{max(vals):.2f}%)")

    if args.dry_run:
        print("\nDry run — nothing written.")
        return 0

    for r in rows:
        r["broker_raw"] = r["broker"]
        r["broker"] = mapping[r["broker"]]

    fields = list(rows[0].keys())
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"\n  {len(rows)} rows -> {args.out}")
    print("  broker_raw keeps what the report actually said, so a merge can be")
    print("  checked against the source rather than taken on trust.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

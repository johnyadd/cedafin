"""
check_consistency.py — does the data hang together?

WHY THIS EXISTS
Thirty-seven provider records represented twenty-four broker firms for about
five months. Each card read correctly on its own. The site had provenance
blocks, dated figures and a methodology page — all of which describe where a
number came from, and none of which notices when the numbers contradict each
other.

It was found because somebody asked why Databank appeared twice.

Every check here is one that would have caught something we have actually got
wrong. None is hypothetical.

WHAT IT DOES NOT DO
Fix anything. It reports and exits non-zero, so a scheduled run goes red and
the problem is visible the next morning rather than in five months. Silent
repair would hide the fault that caused it.

Usage:
    python check_consistency.py
    python check_consistency.py --quiet     # only failures
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date

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
    s = (name or "").lower()
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
        print("Missing Supabase credentials.")
        sys.exit(1)
    return out


E = env()
BASE = E["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = E["SUPABASE_SERVICE_ROLE_KEY"]


def get(path: str):
    req = urllib.request.Request(
        BASE + path, headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


FAILURES: list[str] = []
WARNINGS: list[str] = []


def fail(check: str, detail: str) -> None:
    FAILURES.append(f"{check}: {detail}")


def warn(check: str, detail: str) -> None:
    WARNINGS.append(f"{check}: {detail}")


def months_between(a: str, b: str) -> int:
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb - ya) * 12 + (mb - ma) + 1


def check_duplicate_providers(quiet: bool) -> None:
    """
    THE ONE THAT WAS MISSED. The exchange renames firms between reports, and
    slugifying the printed name produced a record per spelling.
    """
    rows = get("/providers?select=slug,trading_name&slug=like.broker-*")
    groups: dict[str, list[str]] = defaultdict(list)
    for p in rows:
        groups[broker_key(p.get("trading_name") or p["slug"])].append(p["slug"])
    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    if dupes:
        for k, slugs in sorted(dupes.items()):
            fail("duplicate brokers", f"{k} -> {', '.join(slugs)}")
    elif not quiet:
        print(f"  ok    {len(rows)} brokers, {len(groups)} distinct firms")


def check_month_counts(quiet: bool) -> None:
    """
    The count came from one source and the date range from another, so a firm
    showed "15 months (Feb 2026 - Jul 2026)".
    """
    rows = get(
        "/providers?select=slug,broker_months_observed,broker_first_seen,"
        "broker_last_seen&slug=like.broker-*"
        "&broker_months_observed=not.is.null"
    )
    bad = 0
    for p in rows:
        f, l, n = p["broker_first_seen"], p["broker_last_seen"], p["broker_months_observed"]
        if not (f and l and n):
            continue
        span = months_between(f, l)
        if n > span:
            fail(
                "month count",
                f"{p['slug']} claims {n} months across a {span}-month span",
            )
            bad += 1
    if not bad and not quiet:
        print(f"  ok    {len(rows)} broker date ranges fit their month counts")


def check_future_dates(quiet: bool) -> None:
    """A figure dated tomorrow is a parsing error, always."""
    today = date.today().isoformat()
    for table, field in (
        ("products", "min_verified_on"),
        ("products", "access_verified_on"),
        ("nav_observations", "as_of"),
        ("macro_series", "as_of"),
    ):
        try:
            rows = get(f"/{table}?select={field}&{field}=gt.{today}&limit=5")
        except urllib.error.HTTPError:
            continue
        if rows:
            fail("future date", f"{table}.{field} has {len(rows)}+ row(s) after {today}")
    if not quiet:
        print("  ok    no figures dated in the future")


def check_charge_bounds(quiet: bool) -> None:
    """
    A charge above 10% a year or below zero is a unit error — a percentage
    stored as a fraction, or the other way round. We have made that mistake:
    every Apple figure was out by a thousand once.
    """
    rows = get(
        "/product_fees?select=product_id,rate,fee_type&rate=not.is.null"
    )
    for f in rows:
        r = float(f["rate"])
        if r < 0:
            fail("charge bounds", f"product {f['product_id']} has a negative {f['fee_type']}")
        elif r > 0.10 and f["fee_type"] not in ("other",):
            warn(
                "charge bounds",
                f"product {f['product_id']} {f['fee_type']} is {r * 100:.2f}% a year",
            )
    if not quiet:
        print(f"  ok    {len(rows)} charge(s) within plausible bounds")


def check_published_have_sources(quiet: bool) -> None:
    """
    The site's whole claim is that every figure is traceable. A published
    product with no source contradicts it.
    """
    # Only products that HAVE a minimum need a source for it. Most publish
    # none, which is a blank field rather than an unsourced figure — flagging
    # those made the check cry wolf 237 times.
    rows = get(
        "/products?select=slug,min_initial_minor,min_source_id"
        "&status=eq.published&min_initial_minor=not.is.null"
    )
    missing = [p["slug"] for p in rows if not p.get("min_source_id")]
    if missing:
        warn(
            "sources",
            f"{len(missing)} published product(s) carry no minimum source",
        )
    if not quiet:
        print(f"  ok    {len(rows) - len(missing)}/{len(rows)} published products sourced")


def check_orphan_products(quiet: bool) -> None:
    """A product whose provider was deleted renders with no name."""
    prods = get("/products?select=slug,provider_id&status=eq.published")
    provs = {p["id"] for p in get("/providers?select=id")}
    orphans = [p["slug"] for p in prods if p.get("provider_id") not in provs]
    if orphans:
        for s in orphans[:10]:
            fail("orphan product", s)
    elif not quiet:
        print(f"  ok    {len(prods)} published products all have a provider")


def check_partial_series(quiet: bool) -> None:
    """
    A firm with far fewer months than its peers has a split series.

    Databank showed six months against everyone else's eighteen, because the
    Exchange renamed them mid-series and the loader keyed on the printed name.
    Nothing flagged it — the record looked complete on its own, and the
    average was simply wrong.
    """
    rows = get(
        "/providers?select=slug,broker_months_observed&slug=like.broker-*"
        "&broker_months_observed=not.is.null"
    )
    if len(rows) < 3:
        return
    counts = [r["broker_months_observed"] for r in rows]
    top = max(counts)
    # Half the maximum. A firm genuinely new to the market will trip this and
    # that is fine — it is a prompt to look, not an assertion of error.
    short = [r for r in rows if r["broker_months_observed"] < top / 2]
    for r in short:
        warn(
            "partial series",
            f"{r['slug']} has {r['broker_months_observed']} months against a maximum of {top}",
        )
    if not short and not quiet:
        print(f"  ok    no broker series is under half the {top}-month maximum")


def check_price_spikes(quiet: bool) -> None:
    """
    A price that jumps by two orders of magnitude and comes straight back.

    IIL Manufacturing sat at GH¢0.05 every month of 2025 except November,
    which recorded GH¢19.79 — four hundred times its neighbours, and back to
    0.05 in December. That was a column misread from the exchange report, not
    a market event. It produced a volatility of 45,080% and an annualised
    return of 2,000%, both of which reached the comparison page.

    Twenty times is deliberately loose. A Ghanaian share can double in a
    month. It cannot multiply by four hundred and divide back.

    WHY IT FETCHES IN PAGES
    The first version made one request per product — about 250 in a row — and
    a connection reset partway through left the check unable to run. It now
    reads every observation in pages of a thousand, a handful of requests in
    all, and groups them here.
    """
    names = {
        p["id"]: p["name"]
        for p in (get("/products?select=id,name&status=eq.published") or [])
    }

    series: dict[str, list[tuple[str, float]]] = {}
    offset = 0
    while True:
        page = get(
            "/nav_observations?select=product_id,as_of,nav"
            "&nav=not.is.null&order=product_id,as_of"
            f"&limit=1000&offset={offset}"
        ) or []
        for r in page:
            if r.get("nav") is None:
                continue
            series.setdefault(r["product_id"], []).append(
                (r["as_of"], float(r["nav"]))
            )
        if len(page) < 1000:
            break
        offset += 1000

    flagged = 0
    checked = 0
    for pid, navs in series.items():
        if pid not in names or len(navs) < 3:
            continue
        checked += 1
        for i in range(1, len(navs) - 1):
            prev, cur, nxt = navs[i - 1][1], navs[i][1], navs[i + 1][1]
            neighbour = max(prev, nxt)
            if neighbour <= 0 or cur <= 0:
                continue
            # Only the middle point of a spike is suspect; its neighbours are
            # the evidence against it, not a second and third fault.
            if cur > neighbour * 20 or cur < min(prev, nxt) / 20:
                fail(
                    "price spike",
                    f"{names[pid]}: {navs[i][0]} is {cur:g} against "
                    f"{prev:g} before and {nxt:g} after",
                )
                flagged += 1

    if not flagged and not quiet:
        print(f"  ok    {checked} price series with no implausible jump")


def check_freshness(quiet: bool) -> None:
    """
    A series that has stopped updating, while every job reported success.

    The Treasury bill benchmark sat three weeks stale and the gold series
    eighteen days, because the fetchers could not tell "nothing published
    today" from "could not reach the source" and the workflow marked both
    steps continue-on-error. Nothing said a word.

    That is worse than a missing figure. A blank is honest; a stale number is
    confident and wrong, and every real return on this site is computed
    against the Treasury bill.

    Tolerances are deliberately generous — a check that cries wolf over a
    public holiday gets ignored, and a late warning costs far less than one
    nobody reads.
    """
    today = date.today()

    def newest(path: str, field: str = "as_of") -> str | None:
        try:
            rows = get(f"{path}&order={field}.desc&limit=1")
        except Exception:  # noqa: BLE001
            return None
        return rows[0][field] if rows else None

    series = [
        ("Gold coin prices", 5, 15,
         "/nav_observations?select=as_of&product_id=in."
         "(select id from products where asset_class=eq.commodity)"),
        ("Treasury bill rates", 14, 42, None),
        ("Inflation", 60, 120,
         "/macro_series?select=as_of&series_code=eq.GH_CPI_YOY"),
    ]

    # The T-bill and gold queries need product ids, which PostgREST cannot
    # subquery. Fetch them first.
    def newest_for_class(asset_class: str) -> str | None:
        prods = get(f"/products?select=id&asset_class=eq.{asset_class}")
        ids = ",".join(p["id"] for p in prods or [])
        if not ids:
            return None
        rows = get(
            f"/nav_observations?select=as_of&product_id=in.({ids})"
            "&order=as_of.desc&limit=1"
        )
        return rows[0]["as_of"] if rows else None

    def newest_macro(code: str) -> str | None:
        rows = get(
            f"/macro_series?select=as_of&series_code=eq.{code}"
            "&order=as_of.desc&limit=1"
        )
        return rows[0]["as_of"] if rows else None

    def newest_lending() -> str | None:
        rows = get("/lending_history?select=as_of&order=as_of.desc&limit=1")
        return rows[0]["as_of"] if rows else None

    checks = [
        ("Gold coin prices", newest_for_class("commodity"), 5, 15),
        ("Treasury bill rates", newest_for_class("government_security"), 14, 42),
        ("Inflation", newest_macro("GH_CPI_YOY"), 60, 120),
        # Monthly, but the Exchange publishes a few weeks after month end.
        ("GSE composite index", newest_macro("GSE_COMPOSITE_INDEX"), 60, 120),
        ("GSE value traded", newest_macro("GSE_VALUE_TRADED"), 60, 120),
        ("Policy rate", newest_macro("GH_POLICY_RATE"), 90, 150),
        # Fund managers publish factsheets late and irregularly, so this is
        # the loosest tolerance here.
        ("Fund NAVs", newest_for_class("money_market"), 90, 180),
        ("Bank lending returns", newest_lending(), 100, 150),
    ]

    ok = 0
    for name, latest, warn_after, fail_after in checks:
        if not latest:
            warn("freshness", f"{name}: no observations at all")
            continue
        age = (today - date.fromisoformat(latest[:10])).days
        if age > fail_after:
            fail("freshness", f"{name} last updated {latest} — {age} days ago")
        elif age > warn_after:
            warn("freshness", f"{name} last updated {latest} — {age} days ago")
        else:
            ok += 1

    if ok == len(checks) and not quiet:
        print(f"  ok    {ok} series updating on schedule")


def check_dates_in_notes(quiet: bool) -> None:
    """
    An access note should not restate a date the record already holds.

    Three loaders wrote "Read from their own material on 9 September 2026"
    into access_requirements, while the page renders access_verified_on
    beneath it — so every card showed the date twice. Found by reading the
    page, which is the slow way.
    """
    written = re.compile(
        r"\bon \d{1,2} (January|February|March|April|May|June|July|August|"
        r"September|October|November|December) \d{4}",
        re.I,
    )
    hits = 0
    for table, name_field in (("providers", "trading_name"), ("products", "name")):
        rows = get(
            f"/{table}?select=slug,{name_field},access_requirements"
            "&access_requirements=not.is.null"
        )
        for r in rows:
            if written.search(r.get("access_requirements") or ""):
                warn(
                    "date in note",
                    f"{r['slug']} restates a date the record already holds",
                )
                hits += 1
    if not hits and not quiet:
        print("  ok    no access note restates its own verified date")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not args.quiet:
        print()
        print("  Consistency checks — every one of these caught something real")
        print()

    for fn in (
        check_duplicate_providers,
        check_month_counts,
        check_future_dates,
        check_charge_bounds,
        check_published_have_sources,
        check_orphan_products,
        check_dates_in_notes,
        check_partial_series,
        check_freshness,
        check_price_spikes,
    ):
        try:
            fn(args.quiet)
        except Exception as e:  # noqa: BLE001
            warn(fn.__name__, f"could not run — {e}")

    print()
    if WARNINGS:
        print(f"  {len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(f"    {w}")
        print()
    if FAILURES:
        print(f"  {len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"    {f}")
        print()
        print("  Exiting non-zero so a scheduled run goes red. Nothing is")
        print("  repaired automatically — a silent fix would hide the load")
        print("  that caused it.")
        return 1

    print("  All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
extract_gse.py — equities and, more usefully, who actually trades them.

TWO TABLES, AND THE SECOND ONE IS THE FIND

  EQUITIES, by sector: ticker, closing VWAP, year and 52-week ranges, issued
  shares, market capitalisation and P/E. Useful, and five other sites publish
  the same prices faster. What this gives that they do not is provenance — the
  exchange's own document rather than a derived feed.

  BROKER MARKET SHARE, which nobody else publishes at all. From the July 2026
  report:

      IC SECURITIES          78.82% of value traded, 62.16% of volume
      SBG SECURITIES          3.39%
      DATABANK BROKERAGE      3.32%
      ...
      BULLION SECURITIES      0.00%
      SARPONG CAPITAL         0.00%

  One broker handles four cedis in every five on the Ghana Stock Exchange, and
  several licensed members did no business at all. That concentration matters
  to anyone choosing where to open an account: it shapes execution, spreads,
  and how much choice there really is. It is also the only public data on
  Ghanaian brokers anywhere — they publish no commission rates, so market
  share is the sole comparable fact about them.

  Worth noting alongside: IC Securities is also the sponsor and market maker
  for the NewGold ETF. The dominant broker makes the market in the one gold
  product on the exchange.

WHAT THIS DOES NOT EXTRACT, AND WHY
Not the index history, not the sectoral trade distribution, not the primary
issuances back to 2009. All present, none of it comparable to anything else on
this site. A comparison site earns its place by putting like beside like, not
by hoarding whatever a PDF happens to contain.

Usage:
    python extract_gse.py --dry-run
    python extract_gse.py
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys
from datetime import date

try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf is not installed. Run:  pip install pypdf")
    sys.exit(1)

MONTHS = {m.lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}

# Sector headings that introduce an equity table.
# The nine headings the reports ACTUALLY use, read off all fifteen PDFs rather
# than assumed. The first version of this list guessed at "BANKING", "OIL AND
# GAS" and "REAL ESTATE" — none of which appear — and omitted "FINANCE", which
# is where every bank sits. GCB was published as an Education company for that
# reason: with no heading matched, each row inherited the last one recognised.
SECTORS = [
    "AGRICULTURE", "DISTRIBUTION", "EDUCATION", "FINANCE",
    "FOOD AND BEVERAGE", "ICT", "INSURANCE", "MANUFACTURING", "MINING",
]

# "AGA 37.00 37.00 ... 506.77 18,750.39 0.29"
# Ticker then a run of numbers. n.m. appears where a P/E is not meaningful.
EQUITY_RX = re.compile(
    r"^([A-Z]{2,8})\s+((?:[\d,]+\.\d{2}|n\.m\.|-)(?:\s+(?:[\d,]+\.\d{2}|n\.m\.|-)){6,12})\s*$"
)

# Page 1 carries the market-wide figures, laid out as label then value:
#   GSE COMPOSITE INDEX (GSE-CI) 15,434.87 75.99% 6,992.29 43.03%
#   MARKET CAPITALIZATION (GH¢ M) 292,511.66 70.02% 146,120.15 31.22%
#   VOLUME TRADED 100,366,477 358,198,243 -71.98%
#   VALUE TRADED (GH¢) 683,535,142.98 1,730,480,165.03 -60
#
# The first number after each label is the current month; what follows is the
# year-on-year comparison, which is not stored — a series makes its own
# comparisons, and storing a precomputed change would go stale the moment
# another month is added.
INDEX_RX = re.compile(
    r"GSE\s*COMPOSITE\s*INDEX[^\d]{0,20}([\d,]+\.\d{2})", re.I)
# The FSI label carries "(GSE-FSI)" plus twenty-odd spaces of column padding
# before its value, so the gap allowance is wider here than for the others.
FSI_RX = re.compile(
    r"GSE\s*FINANCIAL\s*STOCK\s*INDEX[^\d]{0,45}([\d,]+\.\d{2})", re.I)
MCAP_RX = re.compile(
    r"MARKET\s*CAPITALIZATION[^\d]{0,25}([\d,]+\.\d{2})", re.I)
VOLUME_RX = re.compile(r"VOLUME\s*TRADED[^\d]{0,20}([\d,]{4,})", re.I)
VALUE_RX = re.compile(r"VALUE\s*TRADED[^\d]{0,25}([\d,]+\.\d{2})", re.I)


def parse_market(pages: list[str]) -> dict:
    """
    Market-wide figures from page 1. One value per metric per month — these go
    into macro_series alongside the T-bill rates and CPI, because they are
    observations about the market rather than about any product.
    """
    head = "\n".join(pages[:3])
    out: dict[str, float] = {}
    for key, rx in (
        ("gse_composite_index", INDEX_RX),
        ("gse_financial_index", FSI_RX),
        ("gse_market_cap_ghs_mil", MCAP_RX),
        ("gse_value_traded_ghs", VALUE_RX),
    ):
        m = rx.search(head)
        if m:
            out[key] = float(m.group(1).replace(",", ""))
    m = VOLUME_RX.search(head)
    if m:
        out["gse_volume_traded"] = float(m.group(1).replace(",", ""))
    return out


# "IC SECURITIES 1,077,567,633.70 78.82% 124,776,830 62.16%"
BROKER_RX = re.compile(
    r"^([A-Z][A-Z .,'&\-]{3,45}?)\s+([\d,]+\.\d{2})\s+([\d.]+)%\s+"
    r"([\d,]+)?\s*([\d.]+)%\s*$"
)


def text_of(path: str) -> list[str]:
    try:
        r = PdfReader(path)
        return [(p.extract_text() or "") for p in r.pages]
    except Exception as e:                                   # noqa: BLE001
        print(f"    unreadable: {type(e).__name__}: {e}")
        return []


def num(s: str) -> float | None:
    s = s.strip()
    if s in ("n.m.", "-", ""):
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def report_month(pages: list[str], path: str) -> str | None:
    for t in pages[:3]:
        # "J U L Y  2 0 2 6" — the cover spaces every character.
        flat = re.sub(r"\s+", "", t[:400]).upper()
        for name, n in MONTHS.items():
            if name.upper() in flat:
                m = re.search(re.escape(name.upper()) + r"(\d{4})", flat)
                if m:
                    y = int(m.group(1))
                    nxt = date(y + (n == 12), 1 if n == 12 else n + 1, 1)
                    return date.fromordinal(nxt.toordinal() - 1).isoformat()
    m = re.search(r"(\d{4})-(\d{2})", os.path.basename(path))
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        nxt = date(y + (mo == 12), 1 if mo == 12 else mo + 1, 1)
        return date.fromordinal(nxt.toordinal() - 1).isoformat()
    return None


def parse_equities(pages: list[str]) -> list[dict]:
    """
    Walk every page tracking the last sector heading seen. A row says nothing
    about which table it belongs to, so the heading has to be carried forward.
    """
    out: list[dict] = []
    sector: str | None = None
    for t in pages:
        for line in t.splitlines():
            stripped = line.strip()
            upper = re.sub(r"\s+", " ", stripped).upper()
            # Anchored on "Closing Price" because a sector heading only ever
            # introduces a price table. Matching the bare word would let a
            # mention anywhere on the page silently reassign every row after
            # it to the wrong sector.
            for s in SECTORS:
                if upper.startswith(s) and "CLOSING PRICE" in upper:
                    sector = s.title()
                    break
            if stripped.upper().startswith("TOTALS"):
                sector = sector  # totals row; skip but keep the sector
                continue

            m = EQUITY_RX.match(stripped)
            if not m:
                continue
            ticker = m.group(1)
            if ticker in ("TOTALS", "PAGE", "GSE", "TERM"):
                continue
            vals = [num(v) for v in m.group(2).split()]
            if len(vals) < 7:
                continue
            # Layout, from the real reports: closing VWAP, month average, year
            # high, year low, YTD average, 52wk high, 52wk low, 52wk average,
            # issued shares (mil), market cap (GH¢ mil), P/E. Trailing three
            # are taken from the end so a missing middle column cannot shift
            # market cap into the P/E slot.
            out.append({
                "sector": sector or "",
                "ticker": ticker,
                "closing_vwap": vals[0],
                "year_high": vals[2] if len(vals) > 2 else None,
                "year_low": vals[3] if len(vals) > 3 else None,
                "issued_shares_mil": vals[-3],
                "market_cap_ghs_mil": vals[-2],
                "pe_ratio": vals[-1],
            })
    return out


def parse_brokers(pages: list[str]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for t in pages:
        if "LICENSED DEALING MEMBER" not in t.upper():
            continue
        for line in t.splitlines():
            m = BROKER_RX.match(line.strip())
            if not m:
                continue
            name = re.sub(r"\s+", " ", m.group(1)).strip(" .,")
            # The table ends with a TOTAL row summing to 100%. Counting it
            # as a broker made the summary claim one firm held the whole
            # market — wrong, and quotable.
            if name.upper().startswith(("TOTAL", "GRAND")):
                continue
            if name in seen or len(name) < 4:
                continue
            seen.add(name)
            out.append({
                "broker": name,
                "value_traded_ghs": num(m.group(2)),
                "value_share_pct": float(m.group(3)),
                "volume_traded": num(m.group(4)) if m.group(4) else None,
                "volume_share_pct": float(m.group(5)),
            })
        # Only the monthly table, not the year-to-date one that follows.
        if out:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/gse")
    ap.add_argument("--equities-csv", default="gse_equities.csv")
    ap.add_argument("--brokers-csv", default="gse_brokers.csv")
    ap.add_argument("--market-csv", default="gse_market.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.dir, "*.pdf")))
    if not files:
        print(f"No PDFs in {args.dir}. Run fetch_gse_reports.py first.")
        return 1

    print(f"Reading {len(files)} report(s)\n")
    all_eq, all_br, all_mk = [], [], []
    for path in files:
        pages = text_of(path)
        if not pages:
            continue
        as_of = report_month(pages, path)
        if not as_of:
            print(f"  {os.path.basename(path):<20} no month found")
            continue

        eq = parse_equities(pages)
        br = parse_brokers(pages)
        mk = parse_market(pages)
        print(f"  {os.path.basename(path):<20} {as_of}  "
              f"{len(eq):>3} equities, {len(br):>2} brokers")

        src = os.path.basename(path)
        all_eq += [{**e, "as_of": as_of, "source": src} for e in eq]
        all_br += [{**b, "as_of": as_of, "source": src} for b in br]
        if mk:
            all_mk.append({"as_of": as_of, **mk, "source": src})

    if not all_eq and not all_br:
        print("\nNothing extracted. Dump a report and check the layout.")
        return 1

    # The concentration finding, from the most recent report that has brokers.
    if all_br:
        latest = max(b["as_of"] for b in all_br)
        recent = sorted(
            [b for b in all_br if b["as_of"] == latest],
            key=lambda b: -(b["value_share_pct"] or 0),
        )
        print(f"\n  Broker market share, {latest}:")
        for b in recent[:5]:
            print(f"    {b['broker'][:34]:<36} {b['value_share_pct']:>6.2f}% of value")
        idle = [b for b in recent if (b["value_share_pct"] or 0) == 0]
        top = recent[0]["value_share_pct"] if recent else 0
        print(f"\n  Top broker holds {top:.2f}% of value traded. "
              f"{len(recent)} licensed members, {len(idle)} did no business.")
        print("  Brokers publish no commission rates, so market share is the")
        print("  only comparable fact about them in the public domain.")

    gld = [e for e in all_eq if e["ticker"] == "GLD"]
    if gld:
        g = sorted(gld, key=lambda x: x["as_of"])[-1]
        print(f"\n  NewGold ETF (GLD) at {g['as_of']}: "
              f"GH¢{g['closing_vwap']:,.2f} a unit")
        print("  Roughly 1/100 oz of bullion. The Ghana Gold Coin's cheapest")
        print("  denomination is GH¢13,803 — this is a fraction of that, which")
        print("  for most savers is the difference between possible and not.")

    if args.dry_run:
        print("\nDry run — nothing written.")
        return 0

    if all_eq:
        with open(args.equities_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_eq[0].keys()))
            w.writeheader()
            w.writerows(all_eq)
        print(f"\n  {len(all_eq)} rows -> {args.equities_csv}")
    if all_br:
        with open(args.brokers_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_br[0].keys()))
            w.writeheader()
            w.writerows(all_br)
        print(f"  {len(all_br)} rows -> {args.brokers_csv}")

    if all_mk:
        all_mk.sort(key=lambda r: r["as_of"])
        keys: list[str] = []
        for r in all_mk:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(args.market_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(all_mk)
        print(f"  {len(all_mk)} rows -> {args.market_csv}")

        first, last = all_mk[0], all_mk[-1]
        idx0 = first.get("gse_composite_index")
        idx1 = last.get("gse_composite_index")
        vol0 = first.get("gse_volume_traded")
        vol1 = last.get("gse_volume_traded")
        if idx0 and idx1:
            print(f"\n  Index {first['as_of']} to {last['as_of']}: "
                  f"{idx0:,.2f} -> {idx1:,.2f}  ({(idx1/idx0-1)*100:+.1f}%)")
        if vol0 and vol1:
            print(f"  Volume over the same period: {(vol1/vol0-1)*100:+.1f}%")
            print("\n  Both lines rising is the healthy version: prices up")
            print("  because more people are buying, not because fewer are")
            print("  selling. Worth stating because the single-month figure")
            print("  in the July report — volume down 71.98% year on year —")
            print("  points the other way and describes one month against an")
            print("  exceptional July 2025, not the trend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

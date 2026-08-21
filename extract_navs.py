"""
extract_navs.py — factsheet PDFs into a scoreable series.  v2

WHAT CHANGED FROM v1, and why — every item was found in real Stanbic files,
not anticipated:

1. TWO LAYOUTS. Stanbic redesigned their factsheet template around March 2026.
   Files before it are ~3,100 characters and publish a RETURNS TABLE with no
   NAV; files after are ~3,900 characters and publish a NAV. v1 was written
   against the new one and silently extracted nothing from 40 of 52 files.

2. COLUMN ZIPPING. The old layout is two-column, and pypdf flattens it to all
   labels then all values:
        Upfront Charge / Management Fee / Trustee Fee / Redemption Charge
        N/A / 2.25% (per annum) / 0.40% (per annum) / N/A
   Regex proximity finds nothing there. The labels must be zipped to the values
   positionally.

3. RETURN CHAINING. Old files give monthly returns instead of prices, so a
   synthetic index is compounded from them, base 100. Volatility and drawdown
   need only relative movement, so they remain valid — but the level is an
   INDEX, not a dealing price. Marked series_kind='chained' and never to be
   displayed as a unit price.

4. SHARE CLASSES. SCT reports Main Class 1-year 29.6% and AMC Sub-Class 20.3%
   on the same date. Separate rows, or you publish whichever was parsed first.

5. DISTRIBUTIONS. SCT states it reinvests earnings; PDIF footnotes a payout of
   4.67/unit in April 2026, which is why its NAV fell 111.83 -> 108.79. Price
   return equals total return only for a reinvesting fund.

6. TER IS YTD. Old files label it "(YTD Jun-25)" outright, and the values climb
   through the year. Never publish it as an annual figure.

Requires:  pip install pypdf
Usage:     python extract_navs.py [--compute]
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
import urllib.request
from datetime import date

try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf is not installed. Run:  pip install pypdf")
    sys.exit(1)

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}

ENGINE = os.environ.get("PYTHON_ENGINE_URL", "http://localhost:8000")


def text_of(path: str) -> str:
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception as e:                                   # noqa: BLE001
        print(f"    unreadable: {type(e).__name__}: {e}")
        return ""


def num(s) -> float | None:
    if s in (None, "", "N/A"):
        return None
    try:
        return float(str(s).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# FIRST ATLANTIC (FAAM) LAYOUT
#
# Third provider, third shape. Like the old Stanbic files this is two-column
# and pypdf flattens it to a run of LABELS followed by a run of VALUES:
#
#   Inception date / Currency / Valuation period / Benchmark / Min. investment
#   / Upfront fee / Redemption fee / Share Price (NAV per share) /
#   Management Fee (p.a) / Custody Fee (p.a) / AUM / Custodian / Auditors /
#   Risk Profile
#       ...then 14 values in the same order...
#   April 11, 2022 / Ghanaian Cedi / Daily / Average 91-Day T-bill / GH¢50.00
#   / Nil / Nil / GH¢0.1488 / 1.50% / 0.25% / GHS13.26m / GT Bank (GH) Ltd. /
#   UHY Godwinson / Medium
#
# So the zip is positional, exactly as it was for the Stanbic charges block.
# Regex proximity finds nothing because no value sits near its label.
# ---------------------------------------------------------------------------

FAAM_LABELS = [
    "inception date", "currency", "valuation period", "benchmark",
    "min. investment", "upfront fee", "redemption fee",
    "share price", "management fee", "custody fee", "aum",
    "custodian", "auditors", "risk pro",
]


def _is_faam_label(line: str) -> str:
    low = line.strip().lower()
    for lab in FAAM_LABELS:
        if low.startswith(lab):
            return lab
    return ""


def parse_faam(text: str) -> dict:
    """
    Identify FAAM values by SHAPE, not by position.

    Positional zipping fails here and the failure is silent. The label run is
    not stable:
      FAIF Dec 2024 : 14 labels, including a "Manager" row
      FAIF Feb 2026 : 13 labels, "Manager" dropped
      PIPS Feb 2026 : only 4 labels survive extraction at all, then the values
    Zipping 4 labels onto that value run mapped Benchmark -> GH¢50.00 and read
    the 91-day benchmark and the GH¢50 minimum as if they were NAVs. The
    series then read 91.0 for seven months, dropped to 0.12, and the engine
    reported a -99.90% annual return.

    The shapes are unambiguous instead:
      NAV      GH¢0.xxxx   - a sub-unit cedi price, 3-4 decimals
      minimum  GH¢50.00    - whole cedis
      fees     1.50% / 0.25% - the two percentages next to each other
      AUM      GHS10.03m
    """
    if not re.search(r"First\s+Atlantic", text, re.I):
        return {}

    out: dict = {}

    # NAV: the only sub-unit cedi amount with 3+ decimals.
    navs = re.findall(r"GH[¢C]\s*(0\.\d{3,6})", text)
    if navs:
        out["nav"] = float(navs[0])

    # Minimum: a whole-cedi amount, typically 50.00.
    mins = re.findall(r"GH[¢C]\s*([\d,]+\.\d{2})\b", text)
    whole = [float(m.replace(",", "")) for m in mins
             if float(m.replace(",", "")) >= 1]
    if whole:
        out["min_investment"] = min(whole)

    mgmt = re.search(r"Management\s*Fee[^\n]{0,30}?([\d.]+)\s*%", text, re.I)
    cust = re.search(r"Custody\s*Fee[^\n]{0,30}?([\d.]+)\s*%", text, re.I)
    if not (mgmt and cust):
        # Labels stripped: the management and custody fees are the adjacent
        # pair immediately after the NAV in the value run.
        pair = re.search(r"GH[¢C]\s*0\.\d{3,6}\s*\n\s*([\d.]+)\s*%\s*\n\s*([\d.]+)\s*%",
                         text)
        if pair:
            out["management_fee_pct"] = float(pair.group(1))
            out["trustee_or_custody_fee_pct"] = float(pair.group(2))
    if mgmt:
        out["management_fee_pct"] = float(mgmt.group(1))
    if cust:
        out["trustee_or_custody_fee_pct"] = float(cust.group(1))

    aum = re.search(r"GHS\s*([\d.,]+)\s*([mb])\b", text, re.I)
    if aum:
        out["aum_raw"] = f"GHS{aum.group(1)}{aum.group(2).lower()}"

    cu = re.search(r"([A-Z][A-Za-z ]{2,30}Bank[A-Za-z ()]{0,20})", text)
    if cu:
        out["custodian"] = cu.group(1).strip()

    bm = re.search(r"((?:Average\s+)?\d{2,3}-Day\s+T-bill)", text, re.I)
    if bm:
        out["benchmark"] = bm.group(1).strip()

    inc = re.search(r"([A-Z][a-z]+\s+\d{1,2},\s*\d{4})", text)
    if inc:
        out["inception"] = inc.group(1)

    return out


def parse_period(text: str, filename: str) -> date | None:
    """Both date styles: 'Fact Sheet as of July 2026' and 'as at 30th June 2025'."""
    # FAAM header: "FIXED INCOME FUND / FEBRUARY 28, 2026"
    m = re.search(r"/\s*([A-Z]{3,9})\s+\d{1,2},\s*(\d{4})", text)
    if m and m.group(1).capitalize() in MONTHS:
        return date(int(m.group(2)), MONTHS[m.group(1).capitalize()], 1)

    m = re.search(r"as\s+(?:at|of)\s+\d{1,2}(?:st|nd|rd|th)?\s+([A-Z][a-z]+)\s+(\d{4})",
                  text, re.I)
    if not m:
        m = re.search(r"Fact\s*Sheet\s*as\s*(?:of|at)\s*([A-Z][a-z]+)\s*(\d{4})",
                      text, re.I)
    if m and m.group(1).capitalize() in MONTHS:
        return date(int(m.group(2)), MONTHS[m.group(1).capitalize()], 1)
    m = re.search(r"(\d{4})-(\d{2})", os.path.basename(filename))
    return date(int(m.group(1)), int(m.group(2)), 1) if m else None


def zip_charges(text: str) -> dict[str, float | None]:
    """
    Old two-column layout: a run of labels, then a run of values. Match them by
    position rather than proximity.
    """
    out: dict[str, float | None] = {}
    block = re.search(
        r"Maximum\s*Charges(.*?)(?:Total\s*Expense|Minimum\s*Investment|Name\s*of\s*Scheme)",
        text, re.I | re.S)
    if not block:
        return out
    lines = [l.strip() for l in block.group(1).splitlines() if l.strip()]
    labels = [l for l in lines if re.match(r"^[A-Za-z][A-Za-z ]{3,30}$", l)]
    values = [l for l in lines if re.match(r"^(N/A|[\d.]+\s*%)", l, re.I)]
    for lab, val in zip(labels, values):
        key = lab.lower().replace(" ", "_")
        out[key] = num(re.sub(r"\(.*?\)", "", val))
    return out


def zip_minimums(text: str) -> dict[str, float | None]:
    """
    Same two-column flattening as the charges block:
        Minimum Investment
           Lump Sum
           Debit Order
        GHS20.00
        GHS10.00
    So "Lump Sum" is followed by "Debit Order", not by a number.
    """
    out: dict[str, float | None] = {}
    block = re.search(r"Minimum\s*Investment(.*?)(?:Name\s*of\s*Scheme|The\s*Manager|"
                      r"Cumulative|Statutory|$)", text, re.I | re.S)
    if not block:
        return out
    lines = [l.strip() for l in block.group(1).splitlines() if l.strip()]
    labels = [l for l in lines if re.match(r"^[A-Za-z][A-Za-z ]{3,25}$", l)]
    values = [l for l in lines if re.match(r"^(GHS|GH₵|\d)", l, re.I)]
    for lab, val in zip(labels, values):
        out[lab.lower().replace(" ", "_")] = num(re.sub(r"[^\d.,]", "", val))
    return out


def parse_returns_table(text: str) -> dict[str, dict[str, float]]:
    """
    The performance table, parsed by COLUMN NAME rather than by position.

    The header is not stable between months. Real examples from one fund:
        Jun 2025:  1M 3M 6M 1Yr 3Yr 5Yr Inception          (7 cols, no YTD)
        Aug 2025:  YTD 1M 3M 6M 1Yr 3Yr 5Yr Inception      (8 cols)
        Nov 2025:  YTD 1M 3M 6M 1Yr Inception              (6 cols, no 3Yr/5Yr)

    An earlier version read a fixed header and mapped by position, so the
    arrival of a YTD column shifted every value one place and a YTD figure of
    27.3 was read as a 1-month return. Chained up, that produced a 663%
    annualised return on a money market fund. Absurd enough to catch by eye —
    which is the only reason it was caught.

    Also handled: row order varies (Main Class first in August, AMC Sub-Class
    first in November), labels wrap across lines, and 'N/A' appears mid-row and
    must occupy its column rather than being skipped.
    """
    m = re.search(r"Cumulative\s*Performance\s*Returns\s*\(%\)(.*?)"
                  r"(?:Returns\s*shown|All\s*indicated|Fund\s*Holdings|\*Introduced|$)",
                  text, re.I | re.S)
    if not m:
        return {}
    block = m.group(1)

    # Header: the run of period labels before the first data row.
    head_line = block.splitlines()[0] if block.splitlines() else ""
    header = re.findall(r"\b(YTD|1M|3M|6M|1Yr|3Yr|5Yr|Inception)\b", head_line, re.I)
    if not header:
        return {}
    header = [h if h.upper() != "YTD" else "YTD" for h in header]

    # Join label-only lines onto the row that follows (labels wrap).
    rows, buf = [], ""
    for raw in block.splitlines()[1:]:
        line = raw.strip()
        if not line:
            continue
        if not re.search(r"\d", line) or re.match(r"^\*?[A-Za-z][A-Za-z \-]*$", line):
            buf = (buf + " " + line).strip()
            continue
        rows.append((buf + " " + line).strip() if buf else line)
        buf = ""

    out: dict[str, dict[str, float]] = {}
    for line in rows:
        lm = re.match(r"^\*?\s*([A-Za-z][A-Za-z \-]{2,30}?)\s+((?:-?[\d.]+|N/?A)(?:\s+(?:-?[\d.]+|N/?A))*)\s*$",
                      line, re.I)
        if not lm:
            continue
        label = re.sub(r"\s+", " ", lm.group(1)).strip().strip("-").strip()
        # Keep N/A as a placeholder so later columns stay aligned.
        tokens = re.findall(r"-?\d+\.?\d*|N/?A", lm.group(2), re.I)
        vals: list[float | None] = []
        for t in tokens:
            vals.append(None if re.match(r"N/?A", t, re.I) else float(t))
        mapped = {header[i]: v for i, v in enumerate(vals)
                  if i < len(header) and v is not None}
        if mapped:
            out[label] = mapped
    return out


def extract(path: str) -> list[dict]:
    """One row per share class present in the file."""
    text = text_of(path)
    if not text.strip():
        return []
    as_of = parse_period(text, path)
    if not as_of:
        return []

    faam = parse_faam(text) if re.search(r"First\s+Atlantic", text, re.I) else {}
    new_layout = bool(re.search(r"NAV\s*\(", text, re.I))

    fund, _ = (re.search(r"^\s*(.{3,60}?(?:Fund|Trust)(?:\s+PLC)?)\s*$", text, re.M) or
               [None, None]), None
    m = re.search(r"^\s*([A-Z][A-Za-z ]{3,50}(?:Fund|Trust)(?:\s+PLC)?)\s*$", text, re.M)
    fund_name = m.group(1).strip() if m else os.path.basename(path)

    charges = zip_charges(text)
    mgmt = charges.get("management_fee")
    trustee = charges.get("trustee_fee") or charges.get("custody_fee")
    if mgmt is None:
        mm = re.search(r"Management\s*Fee[^%\n]{0,25}?([\d.]+)\s*%", text, re.I)
        mgmt = num(mm.group(1)) if mm else None
    if trustee is None:
        cm = re.search(r"(?:Custody|Trustee)\s*Fee[^%\n]{0,25}?([\d.]+)\s*%", text, re.I)
        trustee = num(cm.group(1)) if cm else None

    ter_m = re.search(r"Total\s*Expense\s*Ratio\s*(?:\(([^)]*)\))?[^\d%]{0,20}([\d.]+)\s*%",
                      text, re.I) or \
            re.search(r"Expense\s*Ratio\s*(?:\(([^)]*)\))?[^%\n]{0,25}?([\d.]+)\s*%",
                      text, re.I)
    ter = num(ter_m.group(2)) if ter_m else None
    ter_basis = (ter_m.group(1) or "").strip() if ter_m else ""
    ter_is_ytd = bool(re.search(r"ytd", ter_basis, re.I))

    mins = zip_minimums(text)
    minimum = mins.get("lump_sum")
    min_debit_order = mins.get("debit_order")
    if minimum is None:
        min_m = re.search(r"Lump\s*Sum\s*(?:GHS|GH₵)?\s*([\d,]+(?:\.\d+)?)", text, re.I) or \
                re.search(r"Min(?:imum)?\.?\s*Investment[^\d\n]{0,30}([\d,]+(?:\.\d+)?)",
                          text, re.I)
        minimum = num(min_m.group(1)) if min_m else None

    distributes = not re.search(r"does\s+not\s+distribute", text, re.I)
    dist_m = re.search(r"income\s+distribution\s+of\s+([\d.]+)\s*ghs\s+per\s+share", text, re.I)

    trustee_name, _t = (re.search(r"The\s*Trustee\s*([A-Z][A-Za-z .&]{4,45})", text) or [None, None]), None
    tn = re.search(r"The\s*(?:Trustee|Custodian)\s*([A-Z][A-Za-z .&]{4,45})", text)
    sec_no = re.search(r"SEC\s*No\s*([A-Z0-9/\- ]{6,30})", text, re.I)

    base = {
        "file": os.path.basename(path),
        "fund_name": fund_name,
        "as_of": as_of.isoformat(),
        "layout": "2026" if new_layout else "pre-2026",
        "ter_pct": ter,
        "ter_is_ytd": ter_is_ytd,
        "management_fee_pct": mgmt,
        "trustee_or_custody_fee_pct": trustee,
        "min_investment": minimum,
        "min_debit_order": min_debit_order,
        "distributes": distributes,
        "distribution_per_unit": num(dist_m.group(1)) if dist_m else None,
        "trustee_or_custodian": tn.group(1).strip() if tn else "",
        "sec_no": sec_no.group(1).strip() if sec_no else "",
    }

    rows: list[dict] = []
    if faam and faam.get("nav") is not None:
        base.update({k: v for k, v in faam.items()
                     if k in ("min_investment", "management_fee_pct",
                              "trustee_or_custody_fee_pct")})
        base["custodian"] = faam.get("custodian", "")
        rows.append({**base, "share_class": "main", "nav": faam["nav"],
                     "period_return_pct": None, "yield_pct": None,
                     "series_kind": "quoted", "review_required": False,
                     "review_reason": "", "confidence": "high",
                     "aum_raw": faam.get("aum_raw", ""),
                     "benchmark": faam.get("benchmark", ""),
                     "dealing_frequency": faam.get("dealing_frequency", ""),
                     "inception": faam.get("inception", ""),
                     "risk_rating": faam.get("risk_rating", "")})
        return rows

    if new_layout:
        nav_m = re.search(r"NAV\s*\([^)]*\)\s*(?:GHS|GH₵)?\s*([\d,]+\.\d+)", text, re.I)
        yld_m = re.search(r"Weighted\s*Average\s*Yield[^%\n]{0,35}?([\d.]+)\s*%", text, re.I)
        rows.append({**base, "share_class": "main",
                     "nav": num(nav_m.group(1)) if nav_m else None,
                     "period_return_pct": None,
                     "yield_pct": num(yld_m.group(1)) if yld_m else None,
                     "series_kind": "quoted",
                     "review_required": False, "review_reason": "",
                     "confidence": "high" if nav_m else "none"})
    else:
        table = parse_returns_table(text)
        # Class labels are fund-specific and inconsistent:
        #   Cash Trust  -> "SCT"  / "AMC Sub-Class"
        #   Income Fund -> "SIFT" / "SIFTAMC"
        # Testing for the word "sub" filed SIFTAMC as a second MAIN row, and one
        # class silently overwrote the other. Order in the table is the reliable
        # signal: the first non-benchmark row is the primary class. "AMC" is
        # Stanbic's marker for the secondary class in both funds, so it acts as
        # a confirmation rather than the sole test.
        classes = [(lab, per) for lab, per in table.items()
                   if not re.search(r"benchmark", lab, re.I)]

        # Class labels are fund-specific and the ROW ORDER IS NOT STABLE:
        #   Aug 2025:  SCT first,  then AMC Sub-Class
        #   Nov 2025:  AMC Sub-Class first, then Main Class
        #   Mar 2026:  SIFT first, then SIFTAMC
        #
        # An earlier version keyed off position ("index 0 is main"), which
        # silently filed BOTH rows as 'sub' whenever the AMC row came first —
        # the main class vanished and one row overwrote the other.
        #
        # "AMC" is the reliable marker: it appears in "AMC Sub-Class" and in
        # "SIFTAMC", and never in "SCT", "SIFT" or "Main Class". Position is
        # only a fallback for a label carrying no marker at all.
        def classify(label: str, idx: int, labels: list[str]) -> str:
            if re.search(r"amc|\bsub\b", label, re.I):
                return "sub"
            if re.search(r"\bmain\b", label, re.I):
                return "main"
            # No marker: main is whichever row is NOT the marked one.
            marked = [i for i, l in enumerate(labels)
                      if re.search(r"amc|\bsub\b", l, re.I)]
            return "main" if (marked and idx not in marked) else (
                "main" if idx == 0 else "sub")

        labels = [lab for lab, _ in classes]
        for idx, (label, periods) in enumerate(classes):
            share_class = classify(label, idx, labels)
            one_m = periods.get("1M")
            rows.append({**base,
                         "share_class": share_class,
                         "share_class_label": label,
                         "nav": None,
                         "period_return_pct": one_m,
                         "yield_pct": None,
                         "series_kind": "chained",
                         "review_required": False,
                         "review_reason": "",
                         "confidence": "high" if one_m is not None else "low"})
        # A single factsheet must never produce two rows of the same class.
        # That silently happened twice: once when SIFTAMC failed a "sub" test,
        # and again when a position rule filed both rows as sub. Both times one
        # class overwrote the other and the point count looked plausible.
        seen = [r["share_class"] for r in rows]
        if len(seen) != len(set(seen)):
            print(f"    !! {os.path.basename(path)}: duplicate share_class "
                  f"{seen} from labels {[r.get('share_class_label') for r in rows]}")
            print("       Classification is wrong for this layout — do not trust "
                  "this fund's series until fixed.")
            for r in rows:
                r["review_required"] = True
                r["review_reason"] = "duplicate share_class in one factsheet"

        if not rows:
            rows.append({**base, "share_class": "main", "nav": None,
                         "period_return_pct": None, "yield_pct": None,
                         "series_kind": "chained", "review_required": False,
                         "review_reason": "", "confidence": "none"})
    return rows


def fund_key(r: dict) -> str:
    stem = re.sub(r"_?-?_?\d{4}-\d{2}\.pdf$", "", r["file"]).strip("_-. ")
    return f"{stem}::{r.get('share_class','main')}"


# Monthly moves beyond this are unusual enough to want a human to look.
#
# NOT a delete threshold. An earlier version discarded anything above it, which
# would have silently erased the Stanbic Cash Trust main class falling 5-6% a
# month during Ghana's domestic debt restructuring — real losses on real
# government bonds, and precisely the history this product exists to surface.
# A comparison site that quietly deletes a fund's worst period is worse than
# useless.
#
# So: flag, never drop. A flagged row that nobody has reviewed can still be
# caught. A deleted row is gone and no one will ever know it was there.
FLAG_MONTHLY_PCT = 15.0


def chain(rows: list[dict], label: str = "") -> list[dict]:
    """
    Compound monthly returns into an index, base 100. The level is an INDEX,
    never a dealing price.

    Every point is kept. Outliers are marked review_required so a human decides
    whether it is a parser fault or a real market event — a distinction no
    amount of code can make, and one that needed domain knowledge to settle
    even once.
    """
    out, level, flagged = [], 100.0, []
    for r in sorted(rows, key=lambda x: x["as_of"]):
        pr = r.get("period_return_pct")
        if pr is None:
            continue
        level *= (1.0 + pr / 100.0)
        point = {"as_of": r["as_of"], "nav": round(level, 6)}
        if abs(pr) > FLAG_MONTHLY_PCT:
            r["review_required"] = True
            r["review_reason"] = f"monthly return {pr}% exceeds {FLAG_MONTHLY_PCT}%"
            flagged.append((r["as_of"], pr))
        out.append(point)
    if flagged:
        print(f"    ?? {label or 'series'}: {len(flagged)} month(s) need review "
              f"— e.g. {flagged[0][0]} {flagged[0][1]}%")
        print("       KEPT in the series. Could be a parser fault or a real")
        print("       market event. Filter navs.csv on review_required.")
    return out


# A quoted unit price does not change scale. If consecutive NAVs differ by
# more than this factor, the extractor read two DIFFERENT FIELDS, not two
# prices — FAAM's benchmark (91.0) and minimum (50.0) were being read as NAVs,
# giving a series that sat at 91.0 for seven months then dropped to 0.12. The
# engine dutifully reported -99.90% annualised. A market cannot do that to a
# unit price; only a parser can.
MAX_NAV_SCALE_JUMP = 5.0


def flag_scale_jumps(obs: list[dict], label: str) -> list[dict]:
    """Mark, never drop — same rule as the monthly-return guard."""
    bad = []
    for i in range(1, len(obs)):
        a, b = obs[i - 1]["nav"], obs[i]["nav"]
        if a and b and (b / a > MAX_NAV_SCALE_JUMP or a / b > MAX_NAV_SCALE_JUMP):
            bad.append((obs[i]["as_of"], a, b))
    if bad:
        print(f"    !! {label}: {len(bad)} NAV scale jump(s) — "
              f"e.g. {bad[0][0]} {bad[0][1]} -> {bad[0][2]}")
        print("       A unit price cannot do that. The extractor is reading")
        print("       different fields as NAV. DO NOT TRUST this series.")
    return bad


def call_engine(fund: str, obs: list[dict], kind: str) -> None:
    if len(obs) < 2:
        print(f"  {fund}: {len(obs)} usable point(s) — nothing to compute")
        return
    if kind == "quoted":
        flag_scale_jumps(obs, fund)
    payload = {"product_id": fund, "as_of": max(o["as_of"] for o in obs),
               "observations": obs, "benchmarks": {},
               "windows": ["3m", "6m", "1y", "3y"]}
    req = urllib.request.Request(f"{ENGINE}/compute/metrics",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read())
    except Exception as e:                                   # noqa: BLE001
        print(f"  engine unreachable ({e}) — is uvicorn running on {ENGINE}?")
        return
    print(f"\n  {fund}  [{kind}]  {len(obs)} points, "
          f"{out['first_observation']} to {out['last_observation']}")
    for m in out["metrics"]:
        def pct(v):
            return f"{v*100:7.2f}%" if v is not None else "    n/a"
        print(f"    {m['window_code']:>3}  ann {pct(m.get('annualised_return'))}"
              f"  vol {pct(m.get('volatility'))}"
              f"  maxDD {pct(m.get('max_drawdown'))}"
              f"  n={m['observation_count']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/factsheets")
    ap.add_argument("--navs", default="navs.csv")
    ap.add_argument("--products", default="products.csv")
    ap.add_argument("--compute", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.dir, "**", "*.pdf"), recursive=True))
    if not files:
        print(f"No PDFs under {args.dir}")
        return 1

    print(f"Reading {len(files)} factsheets\n")
    rows: list[dict] = []
    for p in files:
        got = extract(p)
        rows += got
        if not args.quiet:
            if not got:
                print(f"  {os.path.basename(p)[:50]:52} NOTHING")
                continue
            for r in got:
                bits = []
                if r.get("nav") is not None:
                    bits.append(f"NAV {r['nav']}")
                if r.get("period_return_pct") is not None:
                    bits.append(f"1M {r['period_return_pct']}%")
                if r.get("ter_pct") is not None:
                    bits.append(f"TER {r['ter_pct']}%{' YTD' if r['ter_is_ytd'] else ''}")
                print(f"  {os.path.basename(p)[:50]:52} {r['as_of']} "
                      f"{r['share_class']:<5} {' · '.join(bits) or 'empty'}")

    if not rows:
        print("\nNothing extracted at all.")
        return 1

    keys = sorted({k for r in rows for k in r})
    with open(args.navs, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(fund_key(r), []).append(r)

    print(f"\n{'='*72}")
    with open(args.products, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fund_class", "points", "first", "last", "series_kind",
                    "latest_nav", "ter_pct", "ter_is_ytd", "management_fee_pct",
                    "trustee_fee_pct", "min_investment", "distributes",
                    "trustee_or_custodian", "sec_no", "rows_needing_review"])
        for k, rs in sorted(by.items()):
            rs.sort(key=lambda r: r["as_of"])
            quoted = [{"as_of": r["as_of"], "nav": r["nav"]}
                      for r in rs if r.get("nav") is not None]
            chained = chain(rs, k)
            obs = quoted if len(quoted) >= len(chained) else chained
            kind = "quoted" if obs is quoted else "chained"
            latest = rs[-1]
            w.writerow([k, len(obs), obs[0]["as_of"] if obs else "",
                        obs[-1]["as_of"] if obs else "", kind,
                        latest.get("nav"), latest.get("ter_pct"),
                        latest.get("ter_is_ytd"), latest.get("management_fee_pct"),
                        latest.get("trustee_or_custody_fee_pct"),
                        latest.get("min_investment"), latest.get("distributes"),
                        latest.get("trustee_or_custodian"), latest.get("sec_no"),
                        sum(1 for r in rs if r.get("review_required"))])
            print(f"  {k:<52} {len(obs):>3} pts  {kind}")
    print(f"{'='*72}")
    print(f"  wrote {args.navs} and {args.products}")
    print("  A 'chained' level is an INDEX built from published monthly returns,")
    print("  not a dealing price. Never display it as one.")

    needs = sum(1 for r in rows if r.get("review_required"))
    if needs:
        print(f"\n  {needs} row(s) MARKED FOR REVIEW — nothing was discarded.")
        print("  In PowerShell:")
        print("    Import-Csv navs.csv | Where-Object { $_.review_required -eq 'True' } |")
        print("      Select-Object file, as_of, share_class, period_return_pct, review_reason")
        print("  Each is either a parser fault or a real market event. Ghana's debt")
        print("  restructuring produced genuine double-digit monthly falls, so an")
        print("  extreme number is not automatically wrong.")

    if args.compute:
        print("\nMetrics via the engine:")
        for k, rs in sorted(by.items()):
            rs.sort(key=lambda r: r["as_of"])
            quoted = [{"as_of": r["as_of"], "nav": r["nav"]}
                      for r in rs if r.get("nav") is not None]
            chained = chain(rs, k)
            obs, kind = ((quoted, "quoted") if len(quoted) >= len(chained)
                         else (chained, "chained"))
            call_engine(k, obs, kind)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
fetch_imf_cpi.py — Ghana monthly CPI from the IMF, as year-on-year inflation.

WHY THE IMF AND NOT GSS
Ghana Statistical Service is the AUTHORITY for Ghanaian CPI, and this does not
replace them. It solves a different problem: backfill. GSS publishes monthly
bulletins, but getting 31 months of history out of them means reading 31 press
releases. The IMF mirrors national statistics through a free, public, purpose
-built SDMX API — one request, the whole series.

THE DIVISION OF LABOUR, and it matters for provenance:

    IMF   history and backfill. Second-hand but machine-readable.
    GSS   the current month, and a cross-check on anything the IMF reports.

The IMF lags national releases by a month or two, so the latest figure will
not be there when you need it. And where the two disagree materially, GSS wins
— they are the source, the IMF is a mirror. A month where they differ is worth
looking at rather than averaging away.

WHAT IT DOES NOT DO
It does not write to the database. It appends rows to benchmarks.csv, which
still goes through load_benchmarks.py with its range checks and its source
records. A figure arriving over an API gets the same review as one typed by
hand — it just arrives faster.

INDEX, NOT PERCENTAGE
The IMF publishes a price INDEX (2010=100 or similar), not an inflation rate.
Year-on-year is computed here as index[m] / index[m-12] - 1, which is exact
rather than rounded to the one decimal place a press release carries. It also
means the first twelve months of any fetch produce no YoY figure — they are
the base for the ones that follow, so ask for more history than you need.

Usage:
    python fetch_imf_cpi.py --probe          # find the endpoint that answers
    python fetch_imf_cpi.py --from 2023-01   # append YoY rows to benchmarks.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import date

HEADERS = {
    "User-Agent": "CediWise/0.1 (benchmark backfill; contact via site)",
    "Accept": "application/json, text/csv, */*",
}

# The IMF moved from a legacy JSON service to an SDMX 3.0 portal and the old
# service is being retired, so several forms are tried. Ghana is GH in the
# legacy IFS codes and GHA in the ISO3-based new ones.
CANDIDATES = [
    ("legacy CompactData / CPI",
     "http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/CPI/"
     "M.GH.PCPI_IX?startPeriod={start}"),
    ("legacy CompactData / IFS",
     "http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/IFS/"
     "M.GH.PCPI_IX?startPeriod={start}"),
    ("sdmxcentral 2.1",
     "https://sdmxcentral.imf.org/ws/public/sdmxapi/rest/data/IMF.STA,CPI/"
     "GHA.CPI._T.IX.M?startPeriod={start}&format=sdmx-json"),
    ("data.imf.org 3.0",
     "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/CPI/"
     "GHA.CPI._T.IX.M?startPeriod={start}"),
]


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def get(url: str, timeout: int = 45) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return getattr(r, "status", 200), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400]
    except Exception as e:                                   # noqa: BLE001
        return 0, str(e).encode()[:200]


def parse_compactdata(blob: bytes) -> dict[str, float]:
    """Legacy SDMX_JSON: CompactData.DataSet.Series.Obs[{@TIME_PERIOD,@OBS_VALUE}]."""
    try:
        doc = json.loads(blob)
    except json.JSONDecodeError:
        return {}
    series = (doc.get("CompactData", {}).get("DataSet", {}).get("Series"))
    if isinstance(series, list):
        series = series[0] if series else None
    if not isinstance(series, dict):
        return {}
    obs = series.get("Obs", [])
    if isinstance(obs, dict):
        obs = [obs]
    out: dict[str, float] = {}
    for o in obs:
        period = o.get("@TIME_PERIOD")
        value = o.get("@OBS_VALUE")
        if period and value not in (None, ""):
            try:
                out[period] = float(value)
            except ValueError:
                pass
    return out


def parse_sdmx_json(blob: bytes) -> dict[str, float]:
    """SDMX-JSON 1.0: dataSets[0].series{...}.observations{index:[value]}."""
    try:
        doc = json.loads(blob)
    except json.JSONDecodeError:
        return {}
    try:
        periods = [
            v["id"]
            for d in doc["structure"]["dimensions"]["observation"]
            if d["id"].upper() in ("TIME_PERIOD", "TIME")
            for v in d["values"]
        ]
        series = next(iter(doc["dataSets"][0]["series"].values()))
        obs = series["observations"]
    except (KeyError, IndexError, StopIteration):
        return {}
    out: dict[str, float] = {}
    for idx, vals in obs.items():
        try:
            out[periods[int(idx)]] = float(vals[0])
        except (ValueError, IndexError, TypeError):
            pass
    return out


def fetch_index(start: str) -> tuple[str, dict[str, float]] | None:
    for label, template in CANDIDATES:
        url = template.format(start=start)
        status, blob = get(url)
        if status != 200 or not blob:
            print(f"  {label:<28} {status or 'no response'}")
            continue
        points = parse_compactdata(blob) or parse_sdmx_json(blob)
        if points:
            print(f"  {label:<28} OK — {len(points)} monthly points")
            return label, points
        print(f"  {label:<28} 200 but nothing parsed "
              f"({blob[:60]!r})")
    return None


def month_end(period: str) -> str:
    """'2026-07' or '2026M07' -> '2026-07-31'."""
    p = period.replace("M", "-")
    y, m = int(p[:4]), int(p[5:7])
    nxt = date(y + (m == 12), 1 if m == 12 else m + 1, 1)
    return date.fromordinal(nxt.toordinal() - 1).isoformat()


def yoy(points: dict[str, float]) -> list[tuple[str, float]]:
    """index[m] / index[m-12] - 1, as a percentage."""
    keyed = {}
    for period, value in points.items():
        p = period.replace("M", "-")
        if len(p) >= 7:
            keyed[p[:7]] = value
    out = []
    for ym, value in sorted(keyed.items()):
        y, m = int(ym[:4]), int(ym[5:7])
        prior = f"{y - 1}-{m:02d}"
        if prior in keyed and keyed[prior]:
            out.append((month_end(ym), round((value / keyed[prior] - 1) * 100, 4)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="2023-01",
                    help="YYYY-MM. Ask for 12 months more than you need — the "
                         "first year is the base for year-on-year.")
    ap.add_argument("--file", default="benchmarks.csv")
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    print(f"Ghana monthly CPI index from {args.start}\n")
    got = fetch_index(args.start)
    if not got:
        print("\nNo endpoint answered with parseable data.")
        print("The IMF is migrating from the legacy service to data.imf.org, so")
        print("the key format may have changed. Open data.imf.org, find Ghana")
        print("CPI, and copy the API URL from the export dialog.")
        return 1

    label, points = got
    rates = yoy(points)
    if not rates:
        print("\nGot index values but no year-on-year — fewer than 13 months.")
        print("Re-run with an earlier --from.")
        return 1

    print(f"\n{len(rates)} year-on-year figures, "
          f"{rates[0][0]} to {rates[-1][0]}")
    for d, v in rates[-8:]:
        print(f"   {d}   {v:6.2f}%")

    if args.probe:
        print("\nProbe only — benchmarks.csv untouched.")
        return 0

    # Never overwrite a GSS figure with an IMF one. GSS is the authority; the
    # IMF is a mirror. Where both exist, the national statistic stands.
    existing: set[tuple[str, str]] = set()
    gss_months: set[str] = set()
    if os.path.exists(args.file):
        with open(args.file, encoding="utf-8") as f:
            for r in csv.DictReader(
                    line for line in f if not line.lstrip().startswith("#")):
                key = ((r.get("series") or "").strip(), (r.get("as_of") or "").strip())
                existing.add(key)
                if key[0] == "GH_CPI_YOY" and "GSS" in (r.get("source_note") or ""):
                    gss_months.add(key[1][:7])

    added = skipped = 0
    with open(args.file, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for as_of, value in rates:
            if ("GH_CPI_YOY", as_of) in existing or as_of[:7] in gss_months:
                skipped += 1
                continue
            w.writerow(["GH_CPI_YOY", as_of, value,
                        f"IMF ({label}), computed year-on-year from monthly index"])
            added += 1

    print(f"\n  {added} rows appended to {args.file}"
          f"{f', {skipped} already present (GSS figures kept)' if skipped else ''}")
    print("  Next: python load_benchmarks.py --dry-run")
    print("\n  These are IMF mirror figures. Verify the most recent months")
    print("  against GSS — they are the authority and they publish sooner.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

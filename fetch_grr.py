"""
fetch_grr.py - the Ghana Reference Rate (GRR) as a series, from its publisher.

The GRR is set by the Ghana Association of Banks (GAB). Banks price loans as
"GRR + margin" (First Atlantic's cedi mortgage: GRR + at least 8%), so the
site needs the rate in force on any date, with a source for each value.

Sources, most authoritative first:
  1. gab.com.gh home page - the current rate and its effective date
  2. gab.com.gh/grr-historic-data - one PDF per year (monthly values; older
     years give no effective day, so those are stored as the 1st of the month)
  3. SECONDARY_2026 below - 2026 months not yet in any GAB yearly PDF, from
     press reports citing GAB. Inserted only where no official value exists;
     an official value for the same date always replaces them.

Writes (only with --apply) to:
  macro_series  series_code='GH_GRR', as_of=effective date, value as a fraction
                (10.18% -> 0.1018, matching GH_CPI_YOY), source_id per value
  sources       one row per GAB PDF, per home-page reading, per press article
Keeps a copy of each GAB PDF in data/sources/gab/ (git-ignored archive).

Usage (repo root, venv active):
    python fetch_grr.py            # dry run: fetch, parse, show what would change
    python fetch_grr.py --apply    # write
Safe to re-run monthly.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from cedafin_env import supabase_config

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

SERIES = "GH_GRR"
HOME = "https://gab.com.gh/"
HISTORY = "https://gab.com.gh/grr-historic-data"
ARCHIVE = Path(__file__).resolve().parent / "data" / "sources" / "gab"
UA = {"User-Agent": "Mozilla/5.0 (compatible; CedafinBot/1.0; +https://cedafin.com)"}

MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
          "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]

# 2026 months not in any GAB yearly PDF yet. Each row: (as_of, value, day_stated, source_key)
SECONDARY_SOURCES = {
    "newsghana-2026-01": {
        "url": "https://www.newsghana.com.gh/ghana-reference-rate-falls-further-as-borrowing-costs-ease/",
        "publisher": "News Ghana (citing the Ghana Association of Banks)",
        "title": "Ghana Reference Rate Falls Further as Borrowing Costs Ease (7 January 2026)",
        "document_date": "2026-01-07",
    },
    "citi-2026-06": {
        "url": "https://www.citinewsroom.com/2026/06/ghana-reference-rate-falls-to-10-02-in-june-extending-downward-trend/",
        "publisher": "Citi Newsroom (citing the Ghana Association of Banks)",
        "title": "Ghana Reference Rate falls to 10.02% in June (3 June 2026)",
        "document_date": "2026-06-03",
    },
    "citi-2026-07": {
        "url": "https://www.citinewsroom.com/2026/07/ghana-reference-rate-climbs-to-10-59-in-july-reversing-months-of-decline/",
        "publisher": "Citi Newsroom (citing the Ghana Association of Banks)",
        "title": "Ghana reference rate climbs to 10.59% in July (1 July 2026); also gives February to June",
        "document_date": "2026-07-01",
    },
    "citi-2026-08": {
        "url": "https://www.citinewsroom.com/2026/08/ghana-reference-rate-increases-to-10-61-in-august-as-lending-conditions-remain-stable/",
        "publisher": "Citi Newsroom (citing the Ghana Association of Banks)",
        "title": "Ghana Reference Rate increases to 10.61% in August (4 August 2026)",
        "document_date": "2026-08-04",
    },
}
SECONDARY_2026 = [
    # as_of,        value,  day stated?, source
    ("2026-01-07", 0.1568, True,  "newsghana-2026-01"),
    ("2026-02-04", 0.1458, True,  "citi-2026-07"),   # 4 Feb from GAB's own Jan-2026 PDF, since removed
    ("2026-03-01", 0.1171, False, "citi-2026-07"),
    ("2026-04-01", 0.1006, False, "citi-2026-07"),
    ("2026-05-01", 0.1003, False, "citi-2026-07"),
    ("2026-06-03", 0.1002, True,  "citi-2026-06"),
    ("2026-07-01", 0.1059, True,  "citi-2026-07"),
    ("2026-08-01", 0.1061, False, "citi-2026-08"),
]


# ----------------------------------------------------------------------------- fetch
def safe_url(url: str) -> str:
    """GAB links some PDFs with raw spaces ('GAB GRR 2021.pdf'); encode them as a browser would."""
    return urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")


def get(url: str) -> bytes:
    req = urllib.request.Request(safe_url(url), headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def parse_home(html: str) -> tuple[str, float] | None:
    """'The Ghana Reference Rate For September 02, 2026 is 10.18%. Effective September 02, 2026'"""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    m = re.search(r"Ghana Reference Rate For ([A-Za-z]+ \d{1,2}, ?\d{4}) is (\d{1,2}(?:\.\d+)?)\s?%", text, re.I)
    if not m:
        return None
    eff = re.search(r"Effective ([A-Za-z]+ \d{1,2}, ?\d{4})", text, re.I)
    d = datetime.strptime((eff.group(1) if eff else m.group(1)).replace(", ", ",").replace(",", ", "),
                          "%B %d, %Y").date()
    return d.isoformat(), round(float(m.group(2)) / 100, 6)


def history_pdf_links(html: str) -> dict[int, str]:
    links = {}
    for href in re.findall(r'href=["\']([^"\']+\.pdf)["\']', html, re.I):
        name = urllib.parse.unquote(href)
        if "GRR" not in name.upper():
            continue
        y = re.search(r"(20\d{2})", name)
        if y:
            links.setdefault(int(y.group(1)), safe_url(urllib.parse.urljoin(HISTORY, href)))
    return dict(sorted(links.items()))


def parse_year_pdf(text: str, year: int) -> list[tuple[str, float, bool]]:
    """Month headings are upper case: 'JANUARY 14.77' or 'JANUARY 15.68 January 07,2026'."""
    out = []
    rx = re.compile(r"\b(" + "|".join(MONTHS) + r")\b[\s*]*(\d{1,2}\.\d{1,2})"
                    r"(?:[\s*]*([A-Z][a-z]+ \d{1,2}\s*,\s*\d{4}))?")
    for m in rx.finditer(text):
        month = MONTHS.index(m.group(1)) + 1
        value = round(float(m.group(2)) / 100, 6)
        if m.group(3):
            try:
                d = datetime.strptime(re.sub(r"\s*,\s*", ", ", m.group(3)), "%B %d, %Y").date()
                out.append((d.isoformat(), value, True))
                continue
            except ValueError:
                pass
        out.append((date(year, month, 1).isoformat(), value, False))
    return out


# ----------------------------------------------------------------------------- REST
class Rest:
    def __init__(self):
        self.base, key = supabase_config()
        self.h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def call(self, method, path, body=None, prefer=None):
        h = dict(self.h)
        if prefer:
            h["Prefer"] = prefer
        req = urllib.request.Request(f"{self.base}/{path}", method=method, headers=h,
                                     data=None if body is None else json.dumps(body).encode())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            sys.exit(f"\n!! {method} {path.split('?')[0]} failed ({e.code}): {e.read().decode(errors='replace')}")

    def source_id(self, s: dict, apply: bool) -> str | None:
        """Find a source by content hash (PDFs) or by url + document_date; create it if absent."""
        if s.get("content_sha256"):
            q = "sources?select=id&content_sha256=eq." + s["content_sha256"]
        else:
            q = ("sources?select=id&url=eq." + urllib.parse.quote(s["url"], safe="")
                 + ("&document_date=eq." + s["document_date"] if s.get("document_date") else ""))
        found = self.call("GET", q) or []
        if found:
            return found[0]["id"]
        if not apply:
            return None
        row = {k: s.get(k) for k in ("kind", "publisher", "title", "url", "document_date",
                                     "storage_path", "content_sha256")}
        return self.call("POST", "sources", [row], prefer="return=representation")[0]["id"]


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    print(f"fetch_grr.py  [{'APPLY' if args.apply else 'DRY RUN - nothing will be written'}]\n")

    official: dict[str, tuple[float, bool, dict]] = {}   # as_of -> (value, day_stated, source)

    # 1. yearly PDFs
    try:
        hist_html = get(HISTORY).decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"!! could not load {HISTORY}: {e}")
    links = history_pdf_links(hist_html)
    print(f"History page lists {len(links)} yearly PDFs: {', '.join(map(str, links))}")
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for year, url in links.items():
        try:
            pdf = get(url)
        except Exception as e:  # noqa: BLE001
            print(f"  !! {year}: could not download ({e})")
            continue
        name = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
        (ARCHIVE / name).write_bytes(pdf)
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf)).pages)
        rows = parse_year_pdf(text, year)
        src = {"kind": "other", "publisher": "Ghana Association of Banks",
               "title": f"Historical values of the Ghana Reference Rate, {year}"
                        + ("" if any(r[2] for r in rows) else " (monthly; effective day not stated, stored as the 1st)"),
               "url": url, "document_date": None,
               "storage_path": f"data/sources/gab/{name}", "content_sha256": hashlib.sha256(pdf).hexdigest()}
        for as_of, v, stated in rows:
            official[as_of] = (v, stated, src)
        span = f"{rows[0][0]} .. {rows[-1][0]}" if rows else "NO VALUES PARSED"
        print(f"  {year}: {len(rows):>2} values  {span}")

    # 2. current rate from the home page
    try:
        cur = parse_home(get(HOME).decode("utf-8", errors="replace"))
    except Exception as e:  # noqa: BLE001
        cur = None
        print(f"!! could not load {HOME}: {e}")
    if cur:
        as_of, v = cur
        official[as_of] = (v, True, {"kind": "other", "publisher": "Ghana Association of Banks",
                                     "title": f"Ghana Reference Rate effective {as_of} (GAB home page)",
                                     "url": HOME, "document_date": as_of})
        print(f"Home page: {v * 100:.2f}% effective {as_of}")
    else:
        print("!! home page: current rate not found (layout changed?)")

    # 3. secondary 2026 rows, only for months with no official value at all
    #    (official dates are exact, e.g. 4 March; a secondary row may sit on the 1st)
    official_months = {d[:7] for d in official}
    secondary = {}
    for as_of, v, stated, key in SECONDARY_2026:
        if as_of[:7] in official_months:
            continue
        s = SECONDARY_SOURCES[key]
        secondary[as_of] = (v, stated, {"kind": "other", **s})

    # sanity: official values must be plausible
    bad = [(d, v) for d, (v, _, _) in {**official, **secondary}.items() if not (0.01 <= v <= 0.60)]
    if bad:
        sys.exit(f"!! implausible values, nothing written: {bad}")

    rest = Rest()
    existing = {r["as_of"]: r for r in (rest.call(
        "GET", f"macro_series?select=as_of,value,source_id&series_code=eq.{SERIES}") or [])}

    inserts, updates = [], []
    for as_of, (v, stated, src) in sorted({**secondary, **official}.items()):
        sid = rest.source_id(src, args.apply)
        cur_row = existing.get(as_of)
        if cur_row is None:
            inserts.append((as_of, v, sid, src, stated))
        elif abs(float(cur_row["value"]) - v) > 1e-9 or (sid and cur_row["source_id"] != sid and as_of in official):
            updates.append((as_of, v, sid, src, stated, float(cur_row["value"])))

    print(f"\nHeld now: {len(existing)} values.  To insert: {len(inserts)}.  To update: {len(updates)}.")
    for as_of, v, _, src, stated, *old in inserts + updates:
        tag = "OFFICIAL " if src["publisher"] == "Ghana Association of Banks" else "secondary"
        chg = f"  (was {old[0] * 100:.2f}%)" if old else ""
        print(f"  {as_of}  {v * 100:6.2f}%  {tag}  {'' if stated else '[day not stated]'}{chg}")

    if not args.apply:
        print("\nDry run complete. Re-run with --apply to write.")
        return

    for as_of, v, sid, *_ in inserts:
        rest.call("POST", "macro_series", [{"series_code": SERIES, "as_of": as_of, "value": v, "source_id": sid}])
    for as_of, v, sid, *_ in updates:
        rest.call("PATCH", f"macro_series?series_code=eq.{SERIES}&as_of=eq.{as_of}",
                  {"value": v, "source_id": sid})
    print(f"\nInserted {len(inserts)}, updated {len(updates)}.")


if __name__ == "__main__":
    main()

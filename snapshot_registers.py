"""
snapshot_registers.py — keep the register, not just what we read from it.

WHY
Nobody publishes a history of who was licensed in Ghana. The Securities and
Exchange Commission maintains a register; it shows today. A firm appears, a
name changes, an entry vanishes, and there is no record that it was ever
different.

That matters most at exactly the moment somebody needs it. When a firm fails,
the first question is when it was struck off — and the only honest answer
available to anyone outside the Commission is "the register does not say".

WHY SEPARATE FROM discover.py
discover.py READS these pages to find providers. This one SAVES them and does
nothing else. Two jobs on purpose: a scraper that also archives stops
archiving the moment the scraping breaks, and the archive is the part that
cannot be rebuilt later.

It imports SEC_PAGES from discover.py rather than repeating seventeen URLs, so
a category added there is snapshotted here without anyone remembering.

WHY RAW HTML
Parsing throws away everything we did not think to extract. An archive exists
for the bits nobody has thought of yet — a column added next year, a footnote,
a date of licence. Store the page.

WHY WRITE AN IDENTICAL FILE
If this month's page is byte-identical to last month's, it still gets written.
A series with months missing because "nothing changed" cannot demonstrate that
nothing changed. These are small pages and the certainty is worth the bytes.

Usage:
    python snapshot_registers.py --dry-run
    python snapshot_registers.py
"""

from __future__ import annotations

import argparse
import hashlib
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import date

OUT_ROOT = "data/sec"

# Minimal, deliberately. The full browser-shaped header set that gets past
# bank sites made every one of these seventeen fail — the register server
# rejects something in it. A bare User-Agent returns 200.
#
# Worth remembering that more headers is not more compatible.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CedafinBot/0.3)"}

try:
    from discover import SEC_PAGES
except ImportError:  # pragma: no cover
    print("Could not import SEC_PAGES from discover.py — run from the project root.")
    sys.exit(1)


def slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str, timeout: int = 40) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return getattr(r, "status", 200), r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:  # noqa: BLE001
        return 0, b""


def previous_digest(name: str, this_month: str) -> tuple[str | None, str | None]:
    """The most recent earlier snapshot of this register, and its hash."""
    if not os.path.isdir(OUT_ROOT):
        return None, None
    months = sorted(
        m for m in os.listdir(OUT_ROOT)
        if os.path.isdir(os.path.join(OUT_ROOT, m)) and m < this_month
    )
    for m in reversed(months):
        p = os.path.join(OUT_ROOT, m, name)
        if os.path.exists(p):
            with open(p, "rb") as fh:
                return m, hashlib.sha256(fh.read()).hexdigest()
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    month = date.today().strftime("%Y-%m")
    out_dir = os.path.join(OUT_ROOT, month)

    print(f"  {len(SEC_PAGES)} register(s), snapshot for {month}")
    print()

    if not args.dry_run:
        os.makedirs(out_dir, exist_ok=True)

    saved = failed = changed = 0

    for category, url in SEC_PAGES:
        name = f"{slug(category)}.html"
        time.sleep(args.delay)
        status, body = fetch(url)

        if status != 200 or not body:
            print(f"    {category[:34]:<36} FAILED ({status})")
            failed += 1
            continue

        digest = hashlib.sha256(body).hexdigest()
        prev_month, prev_digest = previous_digest(name, month)

        if prev_digest is None:
            state = "first"
        elif prev_digest == digest:
            state = "unchanged"
        else:
            state = f"CHANGED since {prev_month}"
            changed += 1

        print(f"    {category[:34]:<36} {len(body):>7,}b  {state}")

        if not args.dry_run:
            with open(os.path.join(out_dir, name), "wb") as fh:
                fh.write(body)
            saved += 1

    print()
    if args.dry_run:
        print("  Dry run — nothing written.")
        return 0

    print(f"  {saved} saved to {out_dir}, {failed} failed")
    if changed:
        print()
        print(f"  {changed} register(s) differ from the last snapshot. That is")
        print("  worth reading — an entry added or removed is a fact nobody")
        print("  else is recording.")
    print()
    print("  Written whether or not the page changed. A snapshot series with")
    print("  gaps cannot demonstrate that nothing happened in the gap.")
    return 1 if failed and not saved else 0


if __name__ == "__main__":
    sys.exit(main())

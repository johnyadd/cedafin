"""
diff_registers.py — what changed on the regulators' registers this month.

WHY THIS EXISTS
snapshot_registers.py saves the SEC's seventeen registers and four of Bank of
Ghana's on the first of every month. Nothing compared one month with the last,
so a newly licensed fund manager, a bank struck off, or a second mortgage
finance company would have arrived in the archive and gone unnoticed.

That was the one gap the checks were entirely blind to. Freshness catches a
series that stops; the spike check catches a wrong value; this catches the
world changing.

WHAT IT DOES
For each saved register page it pulls out the entity names and writes them to
a plain-text list beside the HTML — `<register>.names.txt`, one name per
line, sorted. That list is readable, and because it is committed, `git diff`
shows the change too.

Then, if the previous month exists, it compares the two and writes the result
to `CHANGES.md` in the current month's folder: a dated record of what
appeared and what disappeared, which is itself source material for findings.

THE FAILURE IT MUST NOT HAVE
A regulator redesigns a page. The parser finds no rows. A naive diff then
reports every firm on the register as removed overnight — a false finding of
exactly the kind this site exists not to publish.

So: a page that yields no names is reported as UNREADABLE, never as empty. And
a register that shrinks by more than half in a month is reported as a
SUSPECTED LAYOUT CHANGE for a person to look at, not as a mass deregistration.

A change on a register is news, not an error, so this never fails the job.
Only an unreadable page is worth a warning.

Usage:
    python diff_registers.py                 # latest month vs the one before
    python diff_registers.py --month 2026-10
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys

ROOT = os.path.join("data", "sec")

# Rows shrinking past this fraction in a month are treated as a parse problem
# until a person says otherwise.
SUSPECT_SHRINK = 0.5

ROW_RX = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RX = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)
TAG_RX = re.compile(r"<[^>]+>")


def clean(cell: str) -> str:
    text = html.unescape(TAG_RX.sub(" ", cell))
    return re.sub(r"\s+", " ", text).strip()


def names_from(page: str) -> list[str]:
    """
    One name per table row: the first cell that reads like a name.

    Registers usually lead with a serial number, so the first cell is often
    "1" or "12". Skip cells that are purely numeric or too short to be a
    firm, and take the first that has letters in it.
    """
    out: set[str] = set()
    for row in ROW_RX.findall(page):
        cells = [clean(c) for c in CELL_RX.findall(row)]
        for c in cells:
            if len(c) < 3 or not re.search(r"[A-Za-z]{2}", c):
                continue
            if re.fullmatch(r"[\d\s./-]+", c):
                continue
            out.add(c)
            break
    return sorted(out, key=str.casefold)


def key(name: str) -> str:
    """Comparison form, so 'Ltd.' against 'LTD' is not reported as a change."""
    k = name.casefold()
    k = re.sub(r"[.,]", "", k)
    k = re.sub(r"\b(limited|ltd|plc|company|co)\b", "", k)
    return re.sub(r"\s+", " ", k).strip()


def months() -> list[str]:
    if not os.path.isdir(ROOT):
        return []
    return sorted(
        d for d in os.listdir(ROOT)
        if re.fullmatch(r"\d{4}-\d{2}", d) and os.path.isdir(os.path.join(ROOT, d))
    )


def extract_month(month: str) -> dict[str, list[str] | None]:
    """register slug -> sorted names, or None where the page was unreadable."""
    folder = os.path.join(ROOT, month)
    result: dict[str, list[str] | None] = {}
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith(".html"):
            continue
        slug = fn[:-5]
        with open(os.path.join(folder, fn), encoding="utf-8", errors="replace") as fh:
            names = names_from(fh.read())
        result[slug] = names or None
        if names:
            with open(os.path.join(folder, f"{slug}.names.txt"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(names) + "\n")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="YYYY-MM; defaults to the latest held")
    args = ap.parse_args()

    held = months()
    if not held:
        print(f"  No snapshots under {ROOT}. Run snapshot_registers.py first.")
        return 0

    current = args.month or held[-1]
    if current not in held:
        print(f"  No snapshot for {current}. Held: {', '.join(held)}")
        return 0
    idx = held.index(current)
    previous = held[idx - 1] if idx > 0 else None

    now = extract_month(current)
    before = extract_month(previous) if previous else {}

    print()
    print(f"  Registers, {current}" + (f" against {previous}" if previous else ""))
    print()

    lines = [f"# Register changes, {current}", ""]
    if previous:
        lines += [f"Compared with {previous}.", ""]
    else:
        lines += ["First month held — nothing to compare against yet.", ""]

    unreadable = 0
    changed = 0

    for slug in sorted(now):
        names = now[slug]
        label = slug.replace("-", " ")

        if names is None:
            unreadable += 1
            print(f"  ??    {label:<34} UNREADABLE — no names parsed")
            lines += [f"## {label}", "", "Page could not be read. Check the layout.", ""]
            continue

        prev = before.get(slug)
        if not previous or prev is None:
            print(f"  --    {label:<34} {len(names):>4} entries")
            continue

        now_keys = {key(n): n for n in names}
        prev_keys = {key(n): n for n in prev}
        added = sorted((now_keys[k] for k in now_keys.keys() - prev_keys.keys()), key=str.casefold)
        removed = sorted((prev_keys[k] for k in prev_keys.keys() - now_keys.keys()), key=str.casefold)

        if len(names) < len(prev) * SUSPECT_SHRINK:
            print(
                f"  !!    {label:<34} {len(prev)} -> {len(names)}  "
                "SUSPECTED LAYOUT CHANGE — read before believing"
            )
            lines += [
                f"## {label}",
                "",
                f"Fell from {len(prev)} to {len(names)} entries. More likely the "
                "page changed shape than half the register was struck off; "
                "a person should look before this is reported.",
                "",
            ]
            continue

        if not added and not removed:
            print(f"  ok    {label:<34} {len(names):>4} entries, unchanged")
            continue

        changed += 1
        print(f"  **    {label:<34} {len(prev)} -> {len(names)}")
        lines += [f"## {label}", ""]
        for n in added:
            print(f"          + {n}")
            lines.append(f"- **Added:** {n}")
        for n in removed:
            print(f"          - {n}")
            lines.append(f"- **Removed:** {n}")
        lines.append("")

    with open(os.path.join(ROOT, current, "CHANGES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print()
    if not previous:
        print("  Names extracted. From next month this reports what changed.")
    else:
        print(f"  {changed} register(s) changed, {unreadable} unreadable.")
    print(f"  Written to {os.path.join(ROOT, current, 'CHANGES.md')}")

    if unreadable:
        print()
        print("  An unreadable page is reported as unreadable, never as empty —")
        print("  otherwise a redesign would look like every firm being struck off.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

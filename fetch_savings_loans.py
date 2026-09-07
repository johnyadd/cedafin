"""
fetch_savings_loans.py — who lends when a bank says no.

WHY THIS AND NOT THE MICROFINANCE REGISTER
Our funding page compares 22 banks and then admits, at the foot, that
microfinance institutions, savings and loans companies and digital lenders are
missing — and that they are where businesses refused by banks actually borrow.

Savings and loans companies are the useful half of that gap. There are around
twenty-five, they lend to SMEs, and they are the first place a business goes
when a bank declines. Bounded, relevant, and maintainable.

The microcredit register is not. It runs to hundreds of Tier 2 and Tier 3
institutions, most of them small and regional — money lenders in Sunyani and
Dunkwa. A business in Accra comparing credit gains nothing from a list of two
hundred, and keeping it current would be a job in itself. It is left alone
deliberately rather than overlooked.

WHAT THIS LOADS, AND WHAT IT CANNOT
Names, addresses, telephone numbers, websites and email addresses — everything
the register gives.

Not rates. Bank of Ghana publishes a monthly APR table for banks and no
equivalent for savings and loans companies, so there is nothing to compare on.
These load as providers with contact details and no products, which is the
honest state: we can tell a borrower who exists and how to reach them, and not
what they charge.

That is worth having anyway. A business turned down by a bank currently has no
list at all.

WHY THE CONTACT DETAILS MATTER MORE HERE THAN USUAL
Five of the addresses we took from the SEC broker register turned out not to
work. A register is a starting point, and publishing what it says while being
ready to correct it is the only workable position.

Usage:
    python fetch_savings_loans.py --dry-run
    python fetch_savings_loans.py
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

REGISTER_URL = (
    "https://www.bog.gov.gh/supervision-regulation/registered-institutions/"
    "savings-loans/"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CedafinBot/0.2; comparison site data check)"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*",
}


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


def fetch_register() -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(REGISTER_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return r.read().decode("utf-8", errors="replace")


def cell_text(cell_html: str) -> str:
    """Strip tags, unescape, collapse whitespace."""
    t = re.sub(r"<[^>]+>", " ", cell_html)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def parse(page: str) -> list[dict]:
    """
    The register is a plain HTML table: name, address, phone, fax, website,
    email. Parsed positionally because the columns have no headers to key on
    — which is fragile, so the row count is reported and a sudden change is
    visible rather than silent.
    """
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)
        if len(cells) < 2:
            continue
        vals = [cell_text(c) for c in cells]
        name = vals[0]
        # The page repeats its header row, so filter on the column label
        # itself rather than assuming one header at the top.
        if not name or name.lower().startswith(
            ("bank name", "name", "savings and loan name")
        ):
            continue
        # A URL may appear in any of the later columns depending on whether a
        # fax number is present.
        website = next(
            (v for v in vals[1:] if re.match(r"https?://|^www\.", v, re.I)), ""
        )
        email = next((v for v in vals[1:] if "@" in v and " " not in v), "")
        phone = next(
            (v for v in vals[1:] if re.search(r"\d{3}", v) and "@" not in v
             and not re.match(r"https?://|^www\.", v, re.I)
             and not re.search(r"box|street|road|avenue|accra|tema", v, re.I)),
            "",
        )
        address = vals[1] if len(vals) > 1 else ""
        rows.append(
            {
                "name": name,
                "address": address,
                "phone": phone,
                "website": website,
                "email": email,
            }
        )
    return rows


def slugify(s: str) -> str:
    s = re.sub(r"\b(limited|ltd|plc|company|companies)\b", "", s, flags=re.I)
    s = re.sub(r"[^a-z0-9]+", "-", s.lower())
    return "sl-" + s.strip("-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("  fetching the Bank of Ghana savings and loans register ...")
    rows = parse(fetch_register())
    if not rows:
        print("  nothing parsed — the page structure may have changed")
        return 1

    print(f"  {len(rows)} institution(s)")
    print()

    if args.dry_run:
        for r in rows:
            bits = []
            if r["website"]:
                bits.append("web")
            if r["email"]:
                bits.append("email")
            if r["phone"]:
                bits.append("phone")
            print(f"    {r['name'][:44]:<46} {', '.join(bits) or 'name only'}")
        print()
        have_web = sum(1 for r in rows if r["website"])
        have_mail = sum(1 for r in rows if r["email"])
        print(f"    {have_web} with a website, {have_mail} with an email address")
        print()
        print("    No rates. Bank of Ghana publishes a monthly APR table for")
        print("    banks and no equivalent for these, so there is nothing to")
        print("    compare on — only who exists and how to reach them.")
        return 0

    src = call("GET", f"/sources?url=eq.{REGISTER_URL}&select=id")
    if src:
        source_id = src[0]["id"]
    else:
        from datetime import date

        source_id = call(
            "POST",
            "/sources",
            {
                "kind": "regulator_publication",
                "publisher": "Bank of Ghana",
                "title": "Register of licensed savings and loans companies",
                "url": REGISTER_URL,
                "retrieved_at": date.today().isoformat(),
            },
            prefer="return=representation",
        )[0]["id"]
    print(f"  source {source_id}")

    added = updated = 0
    for r in rows:
        slug = slugify(r["name"])
        body = {
            "slug": slug,
            "legal_name": r["name"],
            "trading_name": r["name"],
            "status": "published",
            "notes": (
                "Savings and loans company licensed by Bank of Ghana. Lends to "
                "businesses and individuals, and is where many borrowers turn "
                "when a bank declines. Bank of Ghana publishes no APR table "
                "for these institutions, so we hold no rates — asked."
            ),
        }
        if r["website"]:
            w = r["website"]
            body["website"] = w if w.startswith("http") else f"https://{w}"
        if r["email"]:
            body["contact_email"] = r["email"]
        if r["phone"]:
            body["contact_phone"] = r["phone"]
        if r["address"]:
            body["office_address"] = r["address"]

        have = call("GET", f"/providers?slug=eq.{slug}&select=id")
        if have:
            call("PATCH", f"/providers?id=eq.{have[0]['id']}", body)
            updated += 1
        else:
            call("POST", "/providers", body)
            added += 1

    print()
    print(f"  {added} added, {updated} updated")
    print()
    print("  A business refused by a bank now has a list. What each of them")
    print("  charges is the next question, and nobody publishes it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

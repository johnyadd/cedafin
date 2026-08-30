"""
match_broker_contacts.py — SEC broker-dealer register onto GSE market share.

WHY THE BROKER PAGE NEEDED THIS
It listed twenty-four firms by how much business they did and gave no way to
reach any of them. Someone deciding where to open an account learned who is
busiest and nothing else — not an address, not a phone number, not a website.

The SEC licenses these firms as broker-dealers and publishes all of it. The
earlier SEC scrape covered Fund Managers, Mutual Funds, Private Funds,
Registrars, ETFs and Securities Exchanges — the fund side of the register.
Broker-dealers sit on their own page and were simply missed.

TWO REGISTERS, DIFFERENT COUNTS
The SEC lists 34 licensed broker-dealers. The exchange's reports name 24 firms
that actually traded. The difference is not an error: a broker-dealer licence
permits dealing in securities generally, and not every holder is an active
dealing member of the Ghana Stock Exchange. Ten firms hold the licence and did
no GSE business in the period — which is worth knowing before opening an
account with one.

A RENAME HIDING AS TWO FIRMS
The GSE reports name both MERBAN STOCKBROKERS (6 months) and UMB STOCKBROKERS
(9 months). Six plus nine is fifteen — the exact number of reports. The SEC
lists only "Merban Stockbrokers Ltd", with website umbcapital.com and email
stockbrokers@myumbbank.com.

Universal Merchant Bank was formerly Merban. This is one firm renamed partway
through the period, and treating it as two understates it in both directions.
The merge is listed explicitly below rather than inferred, because the evidence
is circumstantial and a reader should be able to check the reasoning.

NAME FORMS DIFFER, AS ALWAYS
    SEC                                       GSE
    Black Star Brokerage Limited              BLACKSTAR BROKERAGE
    IC Securities (Ghana) Ltd.                IC SECURITIES
    Laurus Africa Securities Limited          LAURUS SECURITIES
    Chapel Hill Denham Securities (Gh.) Ltd   CHAPELHILL DENHAM SECURITIES

Suffixes, brackets and spacing all vary. Normalised the same way as the bank
match: strip company suffixes and bracketed country qualifiers, then compare.
Anything that does not match exactly is REPORTED, never resolved by similarity
— attaching one broker's phone number to another's market share would be
invisible until someone rang the wrong firm.

Usage:
    python match_broker_contacts.py --dry-run
    python match_broker_contacts.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

SEC_URL = "https://licensees.sec.gov.gh/licensees/BrokerDealer.php"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "text/html,*/*",
}

SUFFIXES = [
    "services limited", "company limited", "limited", "ltd.", "ltd",
    "plc.", "plc", "inc.", "inc",
]

# Bracketed country qualifiers carry no distinguishing information here.
BRACKETS = re.compile(r"\((?:gh|gh\.|ghana)\)", re.I)

# Circumstantial merges, written out so the reasoning can be checked.
EXPLICIT = {
    # UMB was formerly Merban. GSE names both; SEC lists only Merban, with a
    # UMB website and email. Their month counts sum to the report count.
    "UMB STOCKBROKERS": "MERBAN STOCKBROKERS",
    "BLACKSTAR BROKERAGE": "BLACK STAR BROKERAGE",
    "LAURUS SECURITIES": "LAURUS AFRICA SECURITIES",
    "CHAPELHILL DENHAM SECURITIES": "CHAPEL HILL DENHAM SECURITIES",
    "FIRST ATLANTIC BROKERAGE": "FIRST ATLANTIC BROKERS",
    "FIRSTBANC BROKERAGE": "FIRSTBANC BROKERAGE",
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
HDRS = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json", "Prefer": "return=representation"}


def rest(method: str, path: str, body=None, prefer: str | None = None) -> list:
    h = dict(HDRS)
    if prefer:
        h["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}\n  "
                           f"{e.read().decode('utf-8', 'replace')[:300]}") from e


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=40, context=_ctx()) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:                                   # noqa: BLE001
        print(f"  {type(e).__name__}: {str(e)[:100]}")
        return ""


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s.replace("&amp;", "&").replace("&nbsp;", " ")).strip()


def normalise(name: str) -> str:
    s = BRACKETS.sub(" ", name.upper())
    s = re.sub(r"[.,'&]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for suf in SUFFIXES:
        if s.endswith(" " + suf.upper()):
            s = s[: -len(suf) - 1].strip()
            break
    return EXPLICIT.get(s, s)


def clean_url(u: str) -> str | None:
    u = (u or "").strip()
    if not u or u.lower() in ("n/a", "na", "-"):
        return None
    u = re.sub(r"^https?://licensees\.sec\.gov\.gh/+", "", u)
    if not u.startswith(("http://", "https://")):
        u = "https://" + u.lstrip("/")
    return u


def parse_sec(html: str) -> list[dict]:
    tables = re.findall(r"<table\b.*?</table>", html, re.I | re.S)
    if not tables:
        return []
    table = max(tables, key=len)
    out = []
    for tr in re.findall(r"<tr\b.*?</tr>", table, re.I | re.S):
        cells = [strip_tags(c) for c in
                 re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, re.I | re.S)]
        if len(cells) < 6 or not cells[0] or cells[0].lower().startswith("licensee"):
            continue
        out.append({
            "name": cells[0],
            "postal": cells[1],
            "address": cells[2],
            "phone": cells[3],
            "website": cells[4],
            "email": cells[5],
            "regulatory_status": cells[6] if len(cells) > 6 else "",
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="sec_brokers.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"Fetching {SEC_URL}\n")
    html = fetch(SEC_URL)
    if not html:
        return 1
    sec = parse_sec(html)
    if not sec:
        print("No table found. The page layout may have changed.")
        return 1
    print(f"  {len(sec)} licensed broker-dealer(s) on the SEC register")

    by_name = {normalise(r["name"]): r for r in sec}

    provs = rest("GET", "/providers?slug=like.broker-*"
                        "&select=id,slug,legal_name,trading_name,website")
    print(f"  {len(provs)} broker(s) in the database\n")

    matched, missing = [], []
    for p in provs:
        key = normalise(p.get("trading_name") or p.get("legal_name") or "")
        hit = by_name.get(key)
        if hit:
            matched.append((p, hit))
        else:
            missing.append((p, key))

    for p, hit in matched:
        print(f"  ✓ {(p.get('trading_name') or '')[:30]:<32} "
              f"{(hit['email'] or '—')[:34]}")

    if missing:
        print(f"\n  {len(missing)} not matched — reported, not guessed:")
        for p, key in missing:
            print(f"    {(p.get('trading_name') or '')[:32]:<34} "
                  f"normalised to '{key}'")
        print("\n  Similar names are NOT auto-resolved. Attaching one broker's")
        print("  phone number to another's market share would stay invisible")
        print("  until somebody rang the wrong firm.")

    # Licensed but not trading on the exchange in the period covered. Worth
    # knowing before opening an account with one.
    gse_keys = {normalise(p.get("trading_name") or "") for p in provs}
    idle = [r for k, r in by_name.items() if k not in gse_keys]
    if idle:
        print(f"\n  {len(idle)} SEC-licensed broker-dealer(s) with no GSE")
        print("  trading in the reports held:")
        for r in idle[:12]:
            print(f"    {r['name'][:44]}")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sec[0].keys()))
        w.writeheader()
        w.writerows(sec)
    print(f"\n  {len(sec)} rows -> {args.out}")

    if args.dry_run:
        print("\nDry run — database untouched.")
        return 0

    updated = 0
    for p, hit in matched:
        patch: dict = {}
        site = clean_url(hit["website"])
        if site:
            patch["website"] = site
        if hit["email"] and "@" in hit["email"]:
            patch["contact_email"] = hit["email"].strip().lower()
        if hit["phone"]:
            patch["contact_phone"] = hit["phone"].strip()
        if hit["address"]:
            patch["office_address"] = hit["address"].strip()
        # The register's own name, which differs from the exchange's.
        patch["legal_name"] = hit["name"]
        if not patch:
            continue
        try:
            rest("PATCH", f"/providers?id=eq.{p['id']}", patch,
                 prefer="return=minimal")
            updated += 1
        except RuntimeError as e:
            print(f"    {p['slug']}: {str(e)[:120]}")
            break

    print(f"\n  {updated} broker(s) updated with SEC contact details")
    print("\n  These come from the SEC's register — what a firm filed, not")
    print("  proof it answers the phone. Still nothing on commission: the")
    print("  regulator publishes where they are, not what they charge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

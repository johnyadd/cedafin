"""
load_absa_diaspora.py — the first clear yes on the diaspora page.

WHAT CHANGED
Absa's entry on this site said what their mortgage requires and nothing else,
because a mortgage page was what we happened to read.

A scan of their own navigation found the rest: Absa carry the same banner on
the current account, forex current account, savings account and premier
account pages — "Are you a Ghanaian living abroad? Opening an account as a
diasporan has never been this easy and simple. Our team of dedicated Diaspora
consultants are readily available."

So it is not a diaspora PRODUCT. It is the ordinary accounts, opened by
somebody abroad, with staff assigned to help. Which is arguably better, and
nobody else on this site offers it.

THE TERMS, AND WHY THEY MATTER TO SOMEBODY IN LONDON
  Current account: no minimum balance, GHS 21.50 a month.
  Forex current account: no minimum balance, held in foreign currency, and
    can sit alongside a cedi account.
  Documents: valid passport bio-data page or Ghana Card front and back,
    proof of residence, proof of employment if salaried, foreign TIN if a
    US person.

AND THE REQUIREMENT THAT COSTS MONEY
Certification of documents is mandatory for Ghanaians living abroad — by a
lawyer, a notary public, or a court of competent jurisdiction — and the
certifier must be contactable.

That is the second provider on this site to require certification abroad,
after EDC Stockbrokers. Neither states what it costs, because it is not
theirs to charge. A notary in the UK charges per document; an apostille costs
more again. On a no-minimum account the paperwork may be the whole of the
cost of opening it.

WHAT IS NOT CLAIMED
That the application can be completed without travelling. Absa do not say so,
and an online form plus a diaspora consultant is not the same as a stated
remote process.

Usage:
    python load_absa_diaspora.py --dry-run
    python load_absa_diaspora.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-14"

PAGES = {
    "current": "https://www.absa.com.gh/personal/open-a-current-account/",
    "forex": "https://www.absa.com.gh/personal/open-a-forex-current-account/",
    "savings": "https://www.absa.com.gh/personal/open-a-bonus-savings-account/",
    "home": "https://www.absa.com.gh/personal/get-a-home-loan/",
}

TERMS = (
    "Absa publish a standing offer to Ghanaians abroad rather than a separate "
    "diaspora product. The same statement appears on their current account, "
    "forex current account, savings account and premier account pages: \"Are "
    "you a Ghanaian living abroad? Opening an account as a diasporan has "
    "never been this easy and simple. Our team of dedicated Diaspora "
    "consultants are readily available to provide you with expert support on "
    "your account opening journey.\"\n\n"
    "The accounts themselves are the ordinary ones. The current account "
    "requires no minimum balance and charges GHS 21.50 a month, with a debit "
    "card carrying travel insurance cover of up to GHS 100,000. The forex "
    "current account also requires no minimum balance, gives 24-hour access "
    "in foreign currency, and can be held alongside a cedi account.\n\n"
    "Documents for a Ghanaian living abroad: a valid passport bio-data page "
    "or Ghana Card front and back, proof of residence, proof of employment "
    "where salaried, and a foreign tax identification number where the "
    "applicant is a US person.\n\n"
    "The requirement that costs money is certification. Absa state that "
    "evidence of certification of documents is mandatory for Ghanaians living "
    "abroad — by a lawyer, a notary public, or a court of competent "
    "jurisdiction — and that the person certifying must be known and capable "
    "of being contacted. A notary outside Ghana charges per document, so on "
    "an account with no minimum balance the paperwork may cost more than the "
    "opening deposit.\n\n"
    "What Absa do not state is whether the whole process can be completed "
    "without travelling. An online form and a named consultant is not the "
    "same as a published remote route, and we do not present it as one.\n\n"
    "On mortgages they publish terms and no rate: up to GHS 5,000,000; up to "
    "90% finance for home purchase and construction in local currency and 80% "
    "in foreign currency; up to 70% for equity release or home improvement; "
    "maximum debt service ratio of 50% local and 45% foreign currency; tenor "
    "of 5 to 15 years for a fixed rate; property and credit life insurance "
    "included."
)


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
        print("Missing Supabase credentials — run from the project root.")
        sys.exit(1)
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
        print(f"  {e.read().decode('utf-8', 'replace')[:600]}\n")
        raise


def source_for(url: str, title: str) -> str:
    have = call("GET", f"/sources?url=eq.{url}&select=id")
    if have:
        return have[0]["id"]
    return call(
        "POST",
        "/sources",
        {
            "kind": "manual_entry",
            "publisher": "Absa Bank Ghana",
            "title": title,
            "url": url,
            "retrieved_at": VERIFIED_ON,
        },
        prefer="return=representation",
    )[0]["id"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    prov = call("GET", "/providers?slug=eq.absa-bank-ghana&select=id")

    if args.dry_run:
        print()
        print("  Absa Bank Ghana — diaspora access")
        print()
        print("    Not a product. A standing offer across four account types,")
        print("    with dedicated diaspora consultants.")
        print()
        print("    Current account: no minimum balance, GHS 21.50 a month.")
        print("    Forex current: no minimum, 24-hour access, cedi account too.")
        print("    Documents: passport or Ghana Card, residence, employment,")
        print("      foreign TIN for US persons.")
        print("    CERTIFICATION MANDATORY — lawyer, notary or court.")
        print()
        print("    Not claimed: that it can be done without travelling.")
        print()
        print(f"  Provider found: {bool(prov)}")
        return 0

    if not prov:
        print("  absa-bank-ghana not found.")
        return 1

    src = source_for(PAGES["current"], "Absa Ghana current account — diaspora terms")
    for key in ("forex", "savings"):
        source_for(PAGES[key], f"Absa Ghana {key} account — diaspora terms")

    call(
        "PATCH",
        f"/providers?id=eq.{prov[0]['id']}",
        {"access_requirements": TERMS, "access_verified_on": VERIFIED_ON},
    )
    print(f"  Absa diaspora terms recorded (source {src})")

    call(
        "POST",
        "/provider_disclosure?on_conflict=provider_id,field",
        [
            {
                "provider_id": prov[0]["id"],
                "field": "non_resident_access",
                "published_on": VERIFIED_ON,
                "checked_on": VERIFIED_ON,
                "asked_on": None,
                "answered_on": None,
                "source_kind": "provider_site",
                "note": None,
            }
        ],
        prefer="resolution=merge-duplicates",
    )
    print("  Non-resident access recorded as published")

    print()
    print("  This is the first Ghanaian bank on the site whose answer to")
    print("  'can I open an account from London' is a stated yes with terms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

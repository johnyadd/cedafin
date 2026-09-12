"""
load_edc_access.py — a third broker that answers the question, and a minimum
settled by the fund's own accounts.

TWO THINGS LOADED

  EDC Stockbrokers publish a NON RESIDENT section in the eligibility
  requirements on their trading portal. A completed account opening form and a
  mandate card, with the note that non-resident accounts may be subject to
  requirements specific to each country, and that copies of documents should
  be notarised by a foreign authority.

  That notarisation line is the most practically useful thing on our diaspora
  page. Nobody else discloses it, and it is a real obstacle — a notary in
  London charges £50 to £150 a document, and an apostille adds more. Somebody
  weighing whether to invest GH¢1,000 from abroad needs to know the paperwork
  alone may cost them a hundred pounds.

  EDC Ghana Fixed Income Unit Trust takes GH¢50. The fund's own 2019 annual
  financial statements say "Start with as little as GH¢ 50."

WHY GH¢50 AND NOT GH¢120,000
Ecobank's corporate banking page states GH¢120,000 for the same named trust.
The two cannot both be the retail minimum. We take the figure from the fund's
own annual report over one on a corporate banking page, and record the
conflict so a later session does not "correct" it back.

WHAT IS DELIBERATELY NOT LOADED

  The GH¢120,000. Recorded as a conflict to resolve, not published as a fact.

  A 0.5% front load. It appears on a client's purchase contract note that has
  ended up publicly indexed — GH¢5,000 bought, GH¢25 charged. That document
  names an individual, gives their account number and should not be public.
  Citing it would make us party to the exposure, and the figure is not worth
  that. We ask EDC instead.

  A 2% management fee from a third-party aggregator, four years old. Our
  standard is the issuer's own document.

Usage:
    python load_edc_access.py --dry-run
    python load_edc_access.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VERIFIED_ON = "2026-09-09"

BROKER_SLUG = "broker-edc-stockbrokers"
PORTAL_URL = "https://edctradingportal.ecobank.com/IWECI/Content/tradingplatform.html"
REPORT_URL = "https://www.edcghanaagm.innoverex.com/files/FIXED_INCOME_REPORT_2019.pdf"

ACCESS = (
    "EDC Stockbrokers publish eligibility requirements on their trading "
    "portal with a section headed Non Resident: a completed account opening "
    "form and a mandate card. They add that non-resident accounts may be "
    "subject to specific requirements under each country's regulations, that "
    "their customer service officers are available for clarification, and "
    "that copies of documents should be notarised by a foreign authority for "
    "non-residents. Read from their own material on 9 September 2026. The "
    "notarisation requirement is worth costing before you start — a notary "
    "outside Ghana charges a fee per document, and some institutions also "
    "want an apostille. No other Ghanaian provider we track mentions it."
)

CONFLICT_NOTE = (
    "Minimum unresolved between two of the provider's own pages. The fund's "
    "2019 annual financial statements state \"Start with as little as "
    "GH¢50\"; Ecobank's corporate banking page states GH¢120,000 for the same "
    "named trust. We publish the GH¢50 because it comes from the fund's own "
    "accounts rather than a banking page, and have asked EDC which applies "
    "and whether there is more than one class."
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
        print(f"  {e.read().decode('utf-8', 'replace')[:400]}\n")
        raise


def source_for(url: str, title: str, publisher: str) -> str:
    have = call("GET", f"/sources?url=eq.{url}&select=id")
    if have:
        return have[0]["id"]
    return call(
        "POST",
        "/sources",
        {
            "kind": "manual_entry",
            "publisher": publisher,
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

    # Fixed Income ONLY. The GH¢50 comes from the Fixed Income Unit Trust's
    # own annual report, and EDC run three funds — a fallback to whichever
    # name matched first attributed it to the Money Market trust, which is a
    # different product with an unknown minimum.
    fund = call(
        "GET",
        "/products?name=ilike.*EDC*Fixed%20Income*&select=id,slug,name",
    )

    if args.dry_run:
        print("  EDC Stockbrokers — non-resident terms:")
        print()
        print("    A completed account opening form and a mandate card, with")
        print("    requirements varying by country and DOCUMENTS NOTARISED BY")
        print("    A FOREIGN AUTHORITY for non-residents.")
        print()
        print("    Third broker of twenty-four to publish anything on this,")
        print("    and the only Ghanaian provider of any kind to mention")
        print("    notarisation — which is a real cost before you invest.")
        print()
        if fund:
            print(f"  {fund[0]['name']} — minimum GH¢50")
            print("    From the fund's own 2019 annual financial statements.")
        else:
            print("  No matching EDC fund found — check the product name.")
        print()
        print("  NOT loaded: the GH¢120,000 from the corporate banking page")
        print("  (recorded as a conflict), a 0.5% front load from a client's")
        print("  privately-indexed contract note, and a four-year-old fee from")
        print("  a third-party aggregator.")
        return 0

    portal = source_for(
        PORTAL_URL, "EDC trading platform — eligibility requirements", "EDC Stockbrokers"
    )
    have = call("GET", f"/providers?slug=eq.{BROKER_SLUG}&select=id")
    if not have:
        print(f"  {BROKER_SLUG} not found.")
        return 1
    call(
        "PATCH",
        f"/providers?id=eq.{have[0]['id']}",
        {"access_requirements": ACCESS, "access_verified_on": VERIFIED_ON},
    )
    print(f"  updated EDC Stockbrokers (source {portal})")

    if fund:
        report = source_for(
            REPORT_URL,
            "EDC Ghana Fixed Income Unit Trust — annual financial statements 2019",
            "EDC Investments",
        )
        call(
            "PATCH",
            f"/products?id=eq.{fund[0]['id']}",
            {
                "min_initial_minor": 5000,  # GH¢50.00
                "min_verified_on": VERIFIED_ON,
                "min_source_id": report,
                "notes": CONFLICT_NOTE,
            },
        )
        print(f"  updated {fund[0]['name']} — GH¢50 minimum (source {report})")

    print()
    print("  Three of twenty-four brokers now publish something about clients")
    print("  abroad. It was one, this morning.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

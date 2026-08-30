from pypdf import PdfReader
import re
r = PdfReader("data/gse/gse-2026-07.pdf")
terms = ("MARKET MAKER", "MARKET-MAKER", "SPONSOR", "SPONSORING",
         "LDM", "DEALING MEMBER", "ADVISER", "ADVISOR")
for i, p in enumerate(r.pages):
    t = (p.extract_text() or "").upper()
    hits = [x for x in terms if x in t]
    if hits:
        print(f"--- page {i+1}: {hits}")
        for line in (p.extract_text() or "").splitlines():
            if any(x in line.upper() for x in hits):
                print("   ", line.strip()[:100])

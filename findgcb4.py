from pypdf import PdfReader
r = PdfReader("data/gse/gse-2026-07.pdf")
t = (r.pages[12].extract_text() or "")
lines = [l.strip() for l in t.splitlines() if l.strip()]
for j, l in enumerate(lines[:36]):
    print(f"{j:>3} {l[:80]}")

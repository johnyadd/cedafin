from pypdf import PdfReader
r = PdfReader("data/gse/gse-2026-07.pdf")
t = (r.pages[12].extract_text() or "")
lines = [l.strip() for l in t.splitlines() if l.strip()]
for i, l in enumerate(lines):
    if l.startswith("GCB "):
        for j in range(max(0, i-14), i+1):
            print(f"{j:>3} {lines[j][:80]}")
        break

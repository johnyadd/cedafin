from pypdf import PdfReader
r = PdfReader("data/gse/gse-2026-07.pdf")
for i, p in enumerate(r.pages):
    t = p.extract_text() or ""
    if "GCB" in t:
        for line in t.splitlines():
            if line.strip() and (line.isupper() or "GCB" in line):
                print(f"[{i+1}] {line.strip()[:90]}")
        break

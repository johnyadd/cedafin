from pypdf import PdfReader
r = PdfReader("data/gse/gse-2026-07.pdf")
for i, p in enumerate(r.pages):
    t = p.extract_text() or ""
    for line in t.splitlines():
        s = line.strip()
        if s.startswith("GCB ") and s.count(".") > 4:
            print(f"[page {i+1}] {s[:110]}")

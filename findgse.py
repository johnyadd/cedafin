from pypdf import PdfReader
r = PdfReader("data/gse/gse-2026-07.pdf")
for i, p in enumerate(r.pages):
    t = (p.extract_text() or "")
    hits = [k for k in ("GLD","NewGold","BROKER","Broker","Dividend","DIVIDEND") if k in t]
    if hits: print(i+1, hits)

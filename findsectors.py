from pypdf import PdfReader
import re, glob
seen = set()
for f in sorted(glob.glob("data/gse/*.pdf")):
    for p in PdfReader(f).pages:
        for line in (p.extract_text() or "").splitlines():
            s = line.strip()
            m = re.match(r"^([A-Z][A-Z &/]{3,40}?)\s+Closing Price", s)
            if m:
                seen.add(m.group(1).strip())
for s in sorted(seen):
    print(s)

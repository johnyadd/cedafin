from pypdf import PdfReader
import glob, os
files = sorted(glob.glob("data/factsheets/*.pdf"))
print(f"{len(files)} files\n")
for p in files:
    try:
        txt = (PdfReader(p).pages[0].extract_text() or "").strip()
        n = len(txt)
    except Exception as e:
        n, txt = -1, str(e)
    flag = "IMAGE - no text layer" if n == 0 else ("error" if n < 0 else "")
    print(f"{os.path.basename(p)[:52]:55} {n:6} chars  {flag}")

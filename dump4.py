from pypdf import PdfReader
import re
for f in ["Stanbic_Cash_Trust_Fact_Sheet__2024-06.pdf",
          "Stanbic_Income_Fund_Trust_Fact_Sheet__2026-03.pdf"]:
    t = "\n".join((p.extract_text() or "") for p in PdfReader("data/factsheets/"+f).pages)
    m = re.search(r"Cumulative.{0,420}", t, re.S)
    print("="*70); print(f)
    print(repr(m.group(0)) if m else "NO TABLE")

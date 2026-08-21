from pypdf import PdfReader
r = PdfReader("data/factsheets/Stanbic_Cash_Trust_Fact_Sheet__2025-06.pdf")
print(f"pages: {len(r.pages)}")
print(r.pages[1].extract_text() if len(r.pages) > 1 else "single page only")

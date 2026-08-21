from pypdf import PdfReader
print(PdfReader("data/factsheets/Stanbic_Cash_Trust_Fact_Sheet__2025-06.pdf").pages[0].extract_text())

import pypdf

reader = pypdf.PdfReader("uploads/Basic1_Science_Scheme_of_Learning.pdf")
print("=== NOTES ON PAGE 33 ===")
print(reader.pages[32].extract_text())

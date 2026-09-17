import pypdf

reader = pypdf.PdfReader("uploads/Basic1_Mathematics_Scheme_of_Learning.pdf")
print("=== NOTES ON PAGE 29 ===")
print(reader.pages[28].extract_text())

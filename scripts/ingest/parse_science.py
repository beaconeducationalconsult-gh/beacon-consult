import pypdf

reader = pypdf.PdfReader("uploads/Basic1_Science_Scheme_of_Learning.pdf")
print(f"Total pages: {len(reader.pages)}")

# Print page 1 to 5 text in a structured way
for i in range(5):
    print(f"\n--- PAGE {i+1} ---")
    text = reader.pages[i].extract_text()
    print(text[:1500])

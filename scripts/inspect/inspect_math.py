import pypdf

reader = pypdf.PdfReader("uploads/Basic1_Mathematics_Scheme_of_Learning.pdf")
print("Total pages in Math Scheme of Learning:", len(reader.pages))

# Print page 1 and page 2 text
for i in range(2):
    print(f"\n--- PAGE {i+1} ---")
    print(reader.pages[i].extract_text()[:1500])

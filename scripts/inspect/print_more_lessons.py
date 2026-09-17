import pypdf

reader = pypdf.PdfReader("uploads/Basic1_English_Lesson_Plans_Full_Year.pdf")
print("Total pages in English:", len(reader.pages))

# Print pages 4 to 12
for p in range(3, 11):
    print(f"\n=== Page {p+1} ===")
    print(reader.pages[p].extract_text()[:1000])

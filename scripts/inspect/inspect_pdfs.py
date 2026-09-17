import pypdf

def inspect_pdf(path):
    print(f"Inspecting {path}...")
    reader = pypdf.PdfReader(path)
    print(f"Total pages: {len(reader.pages)}")
    # Print first page text
    print("Page 1 text:")
    print(reader.pages[0].extract_text()[:1000])
    print("-" * 50)

inspect_pdf("uploads/Basic1_English_Lesson_Plans_Full_Year.pdf")
inspect_pdf("uploads/Basic1_Science_Scheme_of_Learning.pdf")

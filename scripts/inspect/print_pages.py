import pypdf

def extract_pages(path, pages_list):
    reader = pypdf.PdfReader(path)
    for p_num in pages_list:
        print(f"=== {path} - Page {p_num + 1} ===")
        if p_num < len(reader.pages):
            text = reader.pages[p_num].extract_text()
            print(text)
        else:
            print("[Out of range]")
        print("="*60)

# Let's inspect pages 1 and 2 of English, and pages 1 and 2 of Science
extract_pages("uploads/Basic1_English_Lesson_Plans_Full_Year.pdf", [1, 2, 3])
extract_pages("uploads/Basic1_Science_Scheme_of_Learning.pdf", [1, 2])

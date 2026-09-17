import pypdf

reader = pypdf.PdfReader("uploads/Basic1_English_Lesson_Plans_Full_Year.pdf")
print("=== PAGE 6 FULL ===")
print(reader.pages[5].extract_text())

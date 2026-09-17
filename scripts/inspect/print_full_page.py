import pypdf

reader = pypdf.PdfReader("uploads/Basic1_English_Lesson_Plans_Full_Year.pdf")

print("=== PAGE 5 FULL ===")
print(reader.pages[4].extract_text())

print("=== PAGE 7 FULL ===")
print(reader.pages[6].extract_text())

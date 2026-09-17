import pypdf
import re

reader = pypdf.PdfReader("uploads/Basic1_Science_Scheme_of_Learning.pdf")

print("Let's scan the pages of the Science Scheme of Learning and print the first 1000 characters of each page...")
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    first_lines = [line.strip() for line in text.split("\n") if line.strip()][:5]
    print(f"Page {i+1} first 5 lines: {first_lines}")

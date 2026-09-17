import pypdf

reader = pypdf.PdfReader("uploads/Basic1_Science_Scheme_of_Learning.pdf")
print(f"Total pages: {len(reader.pages)}")

# Print the first line or two of each page
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    header = lines[0] if lines else "EMPTY"
    header2 = lines[1] if len(lines) > 1 else "EMPTY"
    print(f"Page {i+1}: {header} | {header2}")

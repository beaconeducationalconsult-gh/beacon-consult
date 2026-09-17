import pypdf
import re

reader = pypdf.PdfReader("uploads/Basic1_Science_Scheme_of_Learning.pdf")

print("Parsing entire PDF into text...")
full_text = []
for page_idx, page in enumerate(reader.pages):
    full_text.append((page_idx + 1, page.extract_text()))

# Let's see if we can find Week patterns.
# Usually, a table row might look like: "1 \n1 \n1 \n1 \n1 \nMon–\nFri \n1. \nDIVERSIT\nY OF ..." or something similar.
# Let's search for "Week 1", "Week 2", or "Wk" patterns, or numbers at the beginning of lines.
# Let's inspect pages and write them to text files so we can inspect them or analyze.
for page_num, text in full_text[:5]:
    print(f"--- PAGE {page_num} (Length: {len(text)}) ---")
    print(text[:800])
    print("=" * 40)

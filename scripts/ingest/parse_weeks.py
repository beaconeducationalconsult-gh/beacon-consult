import pypdf
import re

reader = pypdf.PdfReader("uploads/Basic1_Science_Scheme_of_Learning.pdf")

# We want to extract details about each Week.
# Let's inspect the page content sequentially and search for week definitions.
for page_idx, page in enumerate(reader.pages):
    text = page.extract_text()
    # Let's search for lines like "Week X" or "Wk X" or "TERM X"
    term_matches = re.findall(r"TERM \d", text)
    week_matches = re.findall(r"\bWk\s+\d+|\bWeek\s+\d+", text, re.IGNORECASE)
    
    print(f"Page {page_idx + 1}: terms={term_matches}, weeks={list(set(week_matches))[:5]}")

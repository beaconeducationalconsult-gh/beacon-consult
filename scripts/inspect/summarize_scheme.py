import pypdf
import re

reader = pypdf.PdfReader("uploads/Basic1_Science_Scheme_of_Learning.pdf")

print("Checking first few pages of Science Scheme of Learning...")
all_text = ""
for page in reader.pages:
    all_text += page.extract_text() + "\n"

# Let's see how many occurrences of "WEEK 1", "WEEK 2", "TERM 1", etc. exist, 
# or let's write a script that parses rows based on lines and matches
lines = all_text.split("\n")
print(f"Total lines: {len(lines)}")

# Let's look for "TERM 1", "TERM 2", "TERM 3"
for term in ["TERM 1", "TERM 2", "TERM 3"]:
    matches = [line for line in lines if term in line]
    print(f"{term} occurrences: {len(matches)} -> {matches}")

# Let's list some lines containing 'Wk Days Strand Sub-strand' or similar
for idx, line in enumerate(lines[:100]):
    if "Strand" in line or "Sub-strand" in line or "B1." in line:
        print(f"L{idx}: {line[:120]}")

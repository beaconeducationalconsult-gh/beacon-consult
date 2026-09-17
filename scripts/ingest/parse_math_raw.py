# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import pypdf

reader = pypdf.PdfReader("uploads/Basic1_Mathematics_Scheme_of_Learning.pdf")
full_text = []
for i, page in enumerate(reader.pages):
    full_text.append(page.extract_text())

with open("math_raw_text.txt", "w") as f:
    for idx, text in enumerate(full_text):
        f.write(f"=== PAGE {idx+1} ===\n")
        f.write(text)
        f.write("\n\n")

print("Saved raw math text to math_raw_text.txt")

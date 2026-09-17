# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

# Let's clean up the text first
text_clean = re.sub(r'\s+', ' ', text)

# Find all indicator codes and the text immediately following them
# Let's search for patterns like: "B1.X.X.X.X [some text]"
# Indicator codes can have 5 parts: e.g. B1.1.1.1.1
# Let's write a regex to find them and extract up to 300 characters of text after them.

indicators = re.findall(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", text_clean)
unique_indicators = sorted(list(set(indicators)))

print(f"Found {len(unique_indicators)} unique indicators in Science Scheme of Learning:")
for code in unique_indicators:
    # Let's find matches and print some text
    matches = [m.start() for m in re.finditer(re.escape(code), text_clean)]
    print(f"\nCode: {code}")
    # Print the text following the first match (if not revision) or look for non-revision one
    for idx, pos in enumerate(matches):
        snippet = text_clean[pos:pos+300]
        if "[REVISION]" not in snippet or idx == len(matches) - 1:
            print(f"  Snippet {idx+1}: {snippet}")
            break

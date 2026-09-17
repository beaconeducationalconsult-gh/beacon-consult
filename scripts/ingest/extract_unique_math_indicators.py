# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("math_raw_text.txt") as f:
    text = f.read()

text_clean = re.sub(r'\s+', ' ', text)

indicators = re.findall(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", text_clean)
unique_indicators = sorted(list(set(indicators)))

print(f"Found {len(unique_indicators)} unique indicators in Math Scheme of Learning:")
for code in unique_indicators:
    matches = [m.start() for m in re.finditer(re.escape(code), text_clean)]
    print(f"\nCode: {code}")
    for idx, pos in enumerate(matches):
        snippet = text_clean[pos:pos+300]
        if "[REVISION]" not in snippet or idx == len(matches) - 1:
            print(f"  Snippet {idx+1}: {snippet}")
            break

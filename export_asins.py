#!/usr/bin/env python3
import json, re, pathlib, string
import pandas as pd  # nécessite pandas + openpyxl

asin_re = re.compile(r'(?:^|[?&])asin=([A-Z0-9]{10})\b')
DIR = pathlib.Path(".")

# fichiers ciblés : 22..40 + a..z
allowed = {f"{i}.json" for i in range(22, 41)}
allowed |= {f"{ch}.json" for ch in string.ascii_lowercase}

asins = set()
for f in sorted(DIR.glob("*.json")):
    if f.name not in allowed:
        continue
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] {f}: {e}")
        continue
    url = str(data.get("QuickDownloadURL", ""))
    m = asin_re.search(url)
    if not m:
        continue
    asins.add(m.group(1).upper())

# Sauvegarde unique en Excel : une colonne "asin"
df = pd.DataFrame(sorted(asins), columns=["asin"])
df.to_excel("asins.xlsx", index=False, sheet_name="ASINs")

print(f"[OK] Exporté {len(df)} ASINs uniques dans asins.xlsx")

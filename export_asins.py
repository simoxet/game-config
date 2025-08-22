#!/usr/bin/env python3
# Exporte tous les ASIN présents dans 22..40.json et a..z.json vers asins.xlsx
import json, re, pathlib, string
import pandas as pd  # nécessite: pandas + openpyxl

asin_re = re.compile(r'(?:^|[?&])asin=([A-Z0-9]{10})\b')
DIR = pathlib.Path(".")

allowed = {f"{i}.json" for i in range(22, 41)}
allowed |= {f"{ch}.json" for ch in string.ascii_lowercase}

rows = []
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
    rows.append({"file": f.name, "asin": m.group(1)})

df = pd.DataFrame(rows)
# Une feuille "ASINs" avec une colonne "asin" + "file" (utile pour info)
with pd.ExcelWriter("asins.xlsx", engine="openpyxl") as xw:
    df.to_excel(xw, index=False, sheet_name="ASINs")

print(f"[OK] Exporté {len(df)} lignes vers asins.xlsx")

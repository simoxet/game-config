#!/usr/bin/env python3
import json, re, random, pathlib, sys, os, string

# Dossier à traiter (par défaut: dossier courant)
DIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")

# Optionnel: rendre le tirage reproductible (utile pour debug)
SEED = os.environ.get("RANDOM_SEED")
if SEED:
    random.seed(SEED)

asin_re = re.compile(r'(?:^|[?&])asin=([A-Z0-9]+)\b')

# --- Définir les fichiers autorisés ---
allowed_names = {f"{i}.json" for i in range(22, 41)}             # 22..40
allowed_names |= {f"{ch}.json" for ch in string.ascii_lowercase}  # a..z
# (si tu veux aussi A..Z, ajoute: allowed_names |= {f"{ch}.json" for ch in string.ascii_uppercase})

# Lister uniquement les fichiers ciblés
files = sorted([p for p in DIR.glob("*.json") if p.name in allowed_names and p.is_file()])

entries = []
for f in files:
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] Impossible de lire {f}: {e}")
        continue
    url = str(data.get("QuickDownloadURL", ""))
    m = asin_re.search(url)
    if not m:
        print(f"[WARN] asin introuvable pour {f}, ignoré.")
        continue
    entries.append((f, data, url, m.group(1)))

if len(entries) < 2:
    print("Pas assez de fichiers avec ASIN pour mélanger.")
    sys.exit(0)

original_asins = [asin for _, _, _, asin in entries]
shuffled_asins = original_asins[:]
random.shuffle(shuffled_asins)

# Évite le cas permutation identique: rotation simple si nécessaire
if all(a == b for a, b in zip(original_asins, shuffled_asins)):
    shuffled_asins = original_asins[1:] + original_asins[:1]

def replace_asin(url, new_asin):
    return re.sub(r'(asin=)[A-Z0-9]+', r'\1' + new_asin, url)

changed = False
for (f, data, url, _old_asin), new_asin in zip(entries, shuffled_asins):
    new_url = replace_asin(url, new_asin)
    if new_url != url:
        data["QuickDownloadURL"] = new_url
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] {f.name}: ASIN -> {new_asin}")
        changed = True

if not changed:
    print("Aucun changement.")

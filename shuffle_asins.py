#!/usr/bin/env python3
import json, re, random, pathlib, sys, os, string, math
from collections import Counter, defaultdict

# Dossier à traiter (par défaut: dossier courant)
DIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")

# Optionnel: graine pour un tirage reproductible (utile pour debug)
SEED = os.environ.get("RANDOM_SEED")
if SEED:
    random.seed(SEED)

asin_re = re.compile(r'(?:^|[?&])asin=([A-Z0-9]+)\b')

# --- Seuls ces fichiers seront modifiés ---
allowed_names = {f"{i}.json" for i in range(22, 41)}             # 22..40
allowed_names |= {f"{ch}.json" for ch in string.ascii_lowercase}  # a..z

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

N = len(entries)
if N < 2:
    print("Pas assez de fichiers avec ASIN pour mélanger.")
    sys.exit(0)

# Ensemble des ASIN uniques trouvés (dans le groupe ciblé)
unique_asins = sorted(set(asin for *_ , asin in entries))
U = len(unique_asins)
if U == 0:
    print("Aucun ASIN unique trouvé.")
    sys.exit(0)

# --------- Construction d'un plan de répartition ----------
# Contrainte voulue : chaque ASIN est utilisé >= 1 fois et <= 3 fois si possible.
MAX_PER_ASIN = 3

if N <= MAX_PER_ASIN * U:
    # Faisable : on peut plafonner à 3 et utiliser tous les ASIN au moins 1 fois
    target_counts = {a: 1 for a in unique_asins}  # commencer à 1 pour "tous utilisés"
    remaining = N - U
    # Liste des ASIN qui ont encore de la capacité (<3)
    capacity = {a: MAX_PER_ASIN - 1 for a in unique_asins}  # -1 car on a déjà mis 1
    asins_with_cap = [a for a in unique_asins for _ in range(capacity[a])]

    random.shuffle(asins_with_cap)
    for i in range(remaining):
        a = asins_with_cap[i]  # il y en a assez car N <= 3U
        target_counts[a] += 1
else:
    # Impossible de respecter "max 3". On choisit la limite minimale possible.
    min_max = math.ceil(N / U)  # borne nécessaire
    print(f"[WARN] Contraintes impossibles: {N} fichiers mais {U} ASIN uniques. "
          f"Max 3 non tenable, utilisation équilibrée avec max {min_max}.")
    target_counts = {a: 1 for a in unique_asins}
    remaining = N - U
    capacity = {a: min_max - 1 for a in unique_asins}
    asins_with_cap = [a for a in unique_asins for _ in range(capacity[a])]
    random.shuffle(asins_with_cap)
    for i in range(remaining):
        a = asins_with_cap[i]
        target_counts[a] += 1

# Construire la "pile" finale d'ASIN selon les multiplicités choisies
pool = []
for a, cnt in target_counts.items():
    pool.extend([a] * cnt)
assert len(pool) == N, "Incohérence dans la construction du pool."
random.shuffle(pool)

def replace_asin(url, new_asin):
    # Remplace la valeur du paramètre asin= dans l'URL (et l'ajoute si besoin)
    if "asin=" in url:
        return re.sub(r'(asin=)[A-Z0-9]+', r'\1' + new_asin, url)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}asin={new_asin}"

# Réécriture des fichiers
changed = False
for (f, data, url, _old_asin), new_asin in zip(entries, pool):
    new_url = replace_asin(url, new_asin)
    if new_url != url:
        data["QuickDownloadURL"] = new_url
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] {f.name}: ASIN -> {new_asin}")
        changed = True

# Petit récap
final_counts = Counter(pool)
print("[INFO] Répartition finale :", dict(final_counts))

if not changed:
    print("Aucun changement.")

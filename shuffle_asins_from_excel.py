#!/usr/bin/env python3
# Mélange les ASIN des fichiers ciblés en les tirant depuis asins.xlsx
# Tu peux ajouter des ASIN dans asins.xlsx (feuille "ASINs", colonne "asin") : ils seront pris en compte.
import json, re, random, pathlib, string, os
from collections import Counter
import pandas as pd

# ==== Réglages ====
EXCEL_PATH = "asins.xlsx"
SHEET_NAME = "ASINs"
COL_NAME = "asin"
USE_ALL_UNIQUE_AT_LEAST_ONCE = True   # Essaie d'utiliser chaque ASIN unique >= 1 fois si possible
MAX_PER_ASIN = None                   # None = pas de limite ; mets 3 si tu veux "≤3 fois par ASIN"

# ================

asin_re = re.compile(r'(?:^|[?&])asin=([A-Z0-9]{10})\b')
DIR = pathlib.Path(".")

allowed = {f"{i}.json" for i in range(22, 41)}
allowed |= {f"{ch}.json" for ch in string.ascii_lowercase}

# 1) Cible: liste des fichiers à modifier + ASIN actuels
entries = []
for f in sorted(DIR.glob("*.json")):
    if f.name not in allowed: 
        continue
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
if N == 0:
    print("[INFO] Aucun fichier ciblé trouvé.")
    raise SystemExit(0)

# 2) Charger l'Excel (ou le générer automatiquement si absent)
def load_asins_from_excel(path=EXCEL_PATH, sheet=SHEET_NAME, col=COL_NAME):
    if not pathlib.Path(path).exists():
        # fallback: on génère un Excel à partir des JSON actuels
        print(f"[WARN] {path} introuvable. Génération depuis les JSON...")
        import pandas as pd
        rows = [{"asin": a} for *_ , a in entries]
        df = pd.DataFrame(rows)
        with pd.ExcelWriter(path, engine="openpyxl") as xw:
            df.to_excel(xw, index=False, sheet_name=sheet)
        return df[col].astype(str).str.upper().tolist()
    df = pd.read_excel(path, sheet_name=sheet)
    # tolère 'asin' ou 'ASIN' etc.
    candidate_cols = [c for c in df.columns if c.strip().lower() == col.lower()]
    if not candidate_cols:
        raise RuntimeError(f"Colonne '{col}' absente de la feuille '{sheet}'.")
    col = candidate_cols[0]
    # Normaliser
    asins = (
        df[col]
        .astype(str)
        .str.strip()
        .str.upper()
        .tolist()
    )
    # Filtrer au format ASIN (10 alphanum)
    asins = [a for a in asins if re.fullmatch(r"[A-Z0-9]{10}", a)]
    return asins

excel_asins = load_asins_from_excel()
if not excel_asins:
    print("[INFO] Aucun ASIN valide dans l'Excel.")
    raise SystemExit(0)

# 3) Construire le 'pool' final de N ASIN tirés de l'Excel
unique = sorted(set(excel_asins))
U = len(unique)

def build_pool():
    pool = []
    # Comptages observés dans l'Excel (si des doublons existent, on les respecte comme pondération)
    base_counts = Counter(excel_asins)

    if USE_ALL_UNIQUE_AT_LEAST_ONCE and U <= N:
        # On place d'abord une occurrence de chaque ASIN unique
        pool.extend(unique)
        remaining = N - len(pool)
        # Capacité restante par ASIN (si MAX_PER_ASIN est défini)
        def cap(a):
            if MAX_PER_ASIN is None:
                return 10**9  # "infini"
            # déjà utilisé 1 fois, donc:
            return max(0, MAX_PER_ASIN - 1)
        # Construire un sac pondéré par (min(capacité, +inf)) et par base_counts
        bag = []
        for a in unique:
            # pondération de base via la présence dans l'Excel (si doublons)
            weight = max(1, base_counts[a]-1)  # -1 car on a déjà posé 1
            weight = min(weight, cap(a))
            bag.extend([a]*weight)
        # Si le sac est vide (ex: MAX_PER_ASIN=1 ou U==N), on remplira aléatoirement avec unique
        if not bag:
            bag = unique[:]
        random.shuffle(bag)
        while len(pool) < N:
            pool.append(bag[(len(pool)-len(unique)) % len(bag)])
    else:
        # Cas général: on pioche au hasard dans l'Excel
        # (si MAX_PER_ASIN est défini, on applique le plafond)
        if MAX_PER_ASIN is None:
            # Tirage simple avec remise
            for _ in range(N):
                pool.append(random.choice(excel_asins))
        else:
            # Respect du plafond MAX_PER_ASIN si possible
            counts = Counter()
            tries = 0
            while len(pool) < N and tries < 10000:
                a = random.choice(excel_asins)
                if counts[a] < MAX_PER_ASIN:
                    pool.append(a)
                    counts[a] += 1
                tries += 1
            # Si on n'a pas réussi à remplir (Excel trop petit), on complète sans plafond
            while len(pool) < N:
                pool.append(random.choice(excel_asins))
    random.shuffle(pool)
    return pool

pool = build_pool()

# 4) Essayer d'éviter que le fichier garde son propre ASIN (no fixed points)
original = [asin for *_ , asin in entries]
def no_fixed_points(assign):
    return all(a != b for a, b in zip(original, assign))

ok = None
for _ in range(800):
    random.shuffle(pool)
    if no_fixed_points(pool):
        ok = pool[:]
        break
if ok is None:
    # petite correction par échanges
    assign = pool[:]
    for i, old in enumerate(original):
        if assign[i] == old:
            for j in range(i+1, len(assign)):
                if assign[j] != old and assign[i] != original[j]:
                    assign[i], assign[j] = assign[j], assign[i]
                    break
    ok = assign

# 5) Écriture
def replace_asin(url, new_asin):
    if "asin=" in url:
        return re.sub(r'(asin=)[A-Z0-9]{10}', r'\1' + new_asin, url)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}asin={new_asin}"

changed = False
for (f, data, url, _old), new_asin in zip(entries, ok):
    new_url = replace_asin(url, new_asin)
    if new_url != url:
        data["QuickDownloadURL"] = new_url
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(f"[OK] {f.name}: {new_asin}")
        changed = True

print(f"[INFO] Pool final: {dict(Counter(ok))}")
if not changed:
    print("Aucun changement.")

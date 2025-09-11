#!/usr/bin/env python3
import json, re, random, pathlib
from collections import Counter

DIR = pathlib.Path(".")
asin_file = DIR / "asins_41_100.txt"

# 1) Charger & valider la liste
if not asin_file.exists():
    print("[ERREUR] asins_41_100.txt introuvable à la racine du repo.")
    raise SystemExit(1)

raw = [line.strip().upper() for line in asin_file.read_text(encoding="utf-8").splitlines() if line.strip()]
valid_re = re.compile(r"^[A-Z0-9]{10}$")

valid, invalid = [], []
for idx, a in enumerate(raw, 1):
    (valid if valid_re.match(a) else invalid).append((idx, a) if not valid_re.match(a) else a)

if invalid:
    print("[WARN] Lignes invalides ignorées (ASIN = 10 alphanum) :")
    for i, a in invalid:
        print(f"  - ligne {i}: '{a}'")

# dédupliquer en gardant l'ordre
seen = set(); asins = []
for a in valid:
    if a not in seen:
        seen.add(a); asins.append(a)

U = len(asins)
if U == 0:
    print("[ERREUR] Aucun ASIN valide dans asins_41_100.txt après filtrage.")
    raise SystemExit(1)

print(f"[INFO] {U} ASIN uniques chargés (41..100).")

# 2) Lister les fichiers cibles 41..100
allowed = {f"{i}.json" for i in range(41, 101)}
asin_url_re = re.compile(r"(?:^|[?&])asin=([A-Z0-9]{10})\b")

entries = []
for f in sorted(DIR.glob("*.json")):
    if f.name not in allowed:
        continue
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] Lecture impossible {f}: {e}")
        continue
    url = str(data.get("QuickDownloadURL", ""))
    m = asin_url_re.search(url)
    if not m:
        print(f"[WARN] asin introuvable pour {f}, ignoré.")
        continue
    entries.append((f, data, url, m.group(1)))

N = len(entries)
if N == 0:
    print("[INFO] Aucun JSON ciblé trouvé (41..100).")
    raise SystemExit(0)

print(f"[INFO] {N} fichiers cibles (41..100).")

# 3) Plan de comptages avec cap à 2 si possible
MAX_PER = 2
target_counts = {a: 0 for a in asins}

if N <= MAX_PER * U:
    if N >= U:
        for a in asins:  # chacun au moins 1 fois
            target_counts[a] = 1
        remaining = N - U
        bag = []
        for a in asins:
            bag.extend([a] * (MAX_PER - 1))  # 1
        random.shuffle(bag)
        for i in range(remaining):
            target_counts[bag[i]] += 1
    else:
        # moins de fichiers que d'ASIN → en choisir N différents
        chos = asins[:]
        random.shuffle(chos)
        for a in chos[:N]:
            target_counts[a] = 1
else:
    # impossible de rester ≤2 : mettre 2 partout puis répartir le surplus
    for a in asins:
        target_counts[a] = MAX_PER
    remaining = N - MAX_PER * U
    order = asins[:]
    random.shuffle(order)
    i = 0
    while remaining > 0:
        target_counts[order[i % U]] += 1
        i += 1
        remaining -= 1
    print(f"[WARN] N={N} > {MAX_PER}×U={MAX_PER*U} : certains ASIN dépasseront 2 (répartition équilibrée).")

# 4) Construire la pile et éviter les "fixed points"
pool = []
for a, cnt in target_counts.items():
    pool.extend([a] * cnt)
assert len(pool) == N, "Incohérence taille pool."
random.shuffle(pool)

original_asins = [old for (_, _, _, old) in entries]
def no_fixed_points(assign):
    return all(a != b for a, b in zip(original_asins, assign))

ok = None
for _ in range(600):
    random.shuffle(pool)
    if no_fixed_points(pool):
        ok = pool[:]
        break
if ok is None:
    assign = pool[:]
    for i, old in enumerate(original_asins):
        if assign[i] == old:
            for j in range(i+1, N):
                if assign[j] != old and assign[i] != original_asins[j]:
                    assign[i], assign[j] = assign[j], assign[i]
                    break
    ok = assign

# 5) Écrire
def replace_asin(url, new_asin):
    if "asin=" in url:
        return re.sub(r"(asin=)[A-Z0-9]{10}", r"\1" + new_asin, url)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}asin={new_asin}"

changed = 0
for (f, data, url, old_asin), new_asin in zip(entries, ok):
    new_url = replace_asin(url, new_asin)
    if new_url != url:
        data["QuickDownloadURL"] = new_url
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] {f.name}: {old_asin} -> {new_asin}")
        changed += 1
    else:
        print(f"[INFO] {f.name}: inchangé (même ASIN tiré)")

print(f"[INFO] Modifiés (41..100): {changed} / {N}")
print("[INFO] Comptages finaux:", dict(Counter(ok)))

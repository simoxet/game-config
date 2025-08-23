#!/usr/bin/env python3
import json, re, random, pathlib, string

DIR = pathlib.Path(".")
asin_file = DIR / "asins.txt"

# --- lire la liste ---
if not asin_file.exists():
    print("[ERREUR] asins.txt introuvable à la racine du repo.")
    raise SystemExit(1)

raw = [line.strip().upper() for line in asin_file.read_text(encoding="utf-8").splitlines() if line.strip()]
valid_asin = re.compile(r"^[A-Z0-9]{10}$")

valid = []
invalid = []
for i, a in enumerate(raw, 1):
    if valid_asin.match(a):
        valid.append(a)
    else:
        invalid.append((i, a))

if invalid:
    print("[WARN] Lignes invalides ignorées (ASIN = 10 alphanum) :")
    for i, a in invalid:
        print(f"  - ligne {i}: '{a}'")

# dédupliquer en gardant l'ordre
seen = set()
asins = []
for a in valid:
    if a not in seen:
        seen.add(a)
        asins.append(a)

if not asins:
    print("[ERREUR] Aucun ASIN valide dans asins.txt après filtrage.")
    raise SystemExit(1)

print(f"[INFO] {len(asins)} ASIN valides chargés.")

# --- cibler les fichiers à modifier ---
allowed = {f"{i}.json" for i in range(22, 41)} | {f"{ch}.json" for ch in string.ascii_lowercase}
asin_re = re.compile(r"(?:^|[?&])asin=([A-Z0-9]{10})\b")

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
    m = asin_re.search(url)
    if not m:
        print(f"[WARN] asin introuvable pour {f}, ignoré.")
        continue
    entries.append((f, data, url, m.group(1)))

if not entries:
    print("[INFO] Aucun JSON ciblé trouvé (22..40, a..z).")
    raise SystemExit(0)

N = len(entries)

# --- fabriquer un tirage aléatoire et éviter les "fixed points"
# répéter la liste si nécessaire pour atteindre N éléments
pool = (asins * ((N // len(asins)) + 1))[:N]
original = [old for (_,_,_,old) in entries]

def no_fixed_points(assign):
    return all(a != b for a, b in zip(original, assign))

ok = None
for _ in range(500):
    random.shuffle(pool)
    if no_fixed_points(pool):
        ok = pool[:]
        break
if ok is None:
    # correction par échanges simples
    assign = pool[:]
    for i, old in enumerate(original):
        if assign[i] == old:
            for j in range(i+1, N):
                if assign[j] != old and assign[i] != original[j]:
                    assign[i], assign[j] = assign[j], assign[i]
                    break
    ok = assign

changed = 0
unchanged = 0

def replace_asin(url, new_asin):
    if "asin=" in url:
        return re.sub(r"(asin=)[A-Z0-9]{10}", r"\1" + new_asin, url)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}asin={new_asin}"

for (f, data, url, old_asin), new_asin in zip(entries, ok):
    new_url = replace_asin(url, new_asin)
    if new_url != url:
        data["QuickDownloadURL"] = new_url
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] {f.name}: {old_asin} -> {new_asin}")
        changed += 1
    else:
        print(f"[INFO] {f.name}: inchangé (même ASIN tiré)")
        unchanged += 1

print(f"[INFO] Résumé: {changed} modifiés, {unchanged} inchangés.")
if changed == 0:
    print("[INFO] Aucun changement écrit (tirage identique).")

# 4️⃣ Parsea el dump (NDJSON + corchetes + comas)
jobs = []
with open(full_report, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        # Saltar arranque/final de array y líneas vacías
        if not line or line in ('[', ']'):
            continue
        # Quitar coma final si la hubiera
        if line.endswith(','):
            line = line[:-1]
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"⚠️ Línea inválida, salto: {e}")
            continue
        jobs.append(obj)

total = 0
killed = 0
for job in jobs:
    if isinstance(job, dict):
        muts = job.get('mutations') or job.get('results') or []
    elif isinstance(job, list):
        muts = job
    else:
        continue

    total += len(muts)
    killed += sum(1 for m in muts if m.get('test_outcome') == 'killed')

score = (killed / total) * 100 if total else 0.0
print(f"💥 Mutation score: {score:.1f}% ({killed}/{total} mutantes)")

if score < MUTATING_MIN_SCORE:
    print(f"❌ Falla: mínimo {MUTATING_MIN_SCORE}%, obtenido {score:.1f}%")
    sys.exit(1)
else:
    print("✅ Mutation testing PASSED")

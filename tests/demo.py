# .bandit.yml
# Configuración para Bandit – análisis estático de seguridad

# 1️⃣ Formato y salida
format: html                  # plain | json | yaml | html
output_file: logs/bandit.html # Ruta donde se guardará el informe

# 2️⃣ Objetivos a analizar
targets:
  - src
  - agents

# 3️⃣ Directorios a excluir del análisis
exclude_dirs:
  - .venv
  - tests
  - docs

# 4️⃣ Tests/chequeos de Bandit a saltar (IDs o nombres)
skips:
  - B101    # assert statements
  - B110    # try_except_pass
  - B311    # pickle.load

# 5️⃣ Umbrales mínimos para reportar
severity_level: MEDIUM        # LOW | MEDIUM | HIGH
confidence_level: MEDIUM      # LOW | MEDIUM | HIGH

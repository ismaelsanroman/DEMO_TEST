# 🧪 Pre-Commit Hooks & Mutation Testing

Este repositorio cuenta con una configuración de *pre-commit* avanzada que integra diversas herramientas para garantizar calidad de código, limpieza, y robustez en los tests mediante *mutation testing*. A continuación se explica cada herramienta, cómo está configurada y cómo se puede ejecutar tanto de forma individual como en conjunto.

---

## ⚙️ Hooks configurados

### ✅ `ruff`

- **Función:** Linting y formateo con una herramienta rápida y moderna que reemplaza `flake8`, `black`, `isort`.
- **Uso en pre-commit:** Automáticamente revisa y formatea el código.
- **Ejecución manual:**
    
    ```bash
    pipenv run ruff check src
    pipenv run ruff format src
    
    ```
    

### 🔤 `codespell`

- **Función:** Detecta errores tipográficos comunes.
- **Ignora:** palabras del fichero `.codespell.ignorewords`.
- **Ejecución manual:**
    
    ```bash
    pipenv run codespell --ignore-words .codespell.ignorewords --skip=.venv
    
    ```
    

### 🧮 `xenon-complexity`

- **Función:** Evalúa la complejidad ciclomática de módulos.
- **Restricciones:**
    - `-max-absolute B`
    - `-max-modules B`
    - `-max-average B`
- **Ejecución manual:**
    
    ```bash
    pipenv run python -m xenon --max-absolute B --max-modules B --max-average B ./src/gen_ai_agent_sdk_lib
    
    ```
    

### 🧬 `mutation-testing`

- **Función:** Ejecuta tests sobre mutaciones generadas con `cosmic-ray` y exige un mínimo de mutantes "muertos" (detenidos por los tests).
- **Score mínimo requerido:** `80%`
- **Salida:** Reporte en `logs/mutating_testing_report.json`
- **Ejecución manual:**
    
    ```bash
    pipenv run python scripts/mutation_check.py
    
    ```
    

---

## 🔁 Ejecución de todos los hooks

Puedes ejecutar todos los hooks configurados en `pre-commit-config.yaml` con:

```bash
pipenv run pre-commit run --all-files

```

Esto te permite validar todo el proyecto antes de realizar un `commit`, garantizando que el código cumpla los estándares definidos.

---

## 📂 Archivos clave

| Archivo | Descripción |
| --- | --- |
| `.pre-commit-config.yaml` | Define los hooks y sus parámetros. |
| `pyproject.toml` | Contiene configuración de `ruff`, `xenon`, `coverage`, `cosmic-ray`, `pytest`, `hypothesis`. |
| `scripts/mutation_check.py` | Script personalizado para ejecutar `cosmic-ray`, analizar resultados y forzar exit si el score es bajo. |
| `config.toml` | Configuración detallada de `cosmic-ray`: runner, timeout, exclusiones, etc. |
| `cr_session.sqlite` | Base de datos usada por `cosmic-ray`. |
| `logs/mutating_testing_report.json` | Salida en formato JSON del reporte de mutantes. |

---

## 📊 Resultado esperado en consola

- Al fallar:
    
    ```
    Mutation score: 50.0% (3/6 total mutants killed)
    --- Mutation testing FAILED: minimum 80.0%, obtained 50.0%
    
    ```
    
- Al pasar:
    
    ```
    Mutation score: 87.5% (14/16 total mutants killed)
    Mutation testing PASSED
    
    ```
    

---

## 📌 Recomendaciones

- ⚠️ Si un hook falla, corrige antes de hacer commit.
- 🔁 Ejecuta `pre-commit run --all-files` antes de subir cambios a `main`.
- 🧪 Revisa mutantes vivos: pueden indicar tests incompletos.

---

Si necesitas ejecutar alguna parte de este sistema de forma separada, recuerda activar primero el entorno:

```bash
pipenv shell

```

Y luego ejecutar los comandos indicados para cada herramienta. Este entorno garantiza que todas las dependencias estén controladas y alineadas con el proyecto.

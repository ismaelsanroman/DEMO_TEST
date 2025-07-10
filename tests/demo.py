# 🛡️ Plan de Calidad con Pre-commit Hooks & Mutation Testing

Este documento describe la implementación y uso de un sistema robusto de calidad basado en hooks de `pre-commit` y pruebas avanzadas, enfocado en garantizar la calidad, seguridad y mantenibilidad del código.

---

## 🎯 Objetivos

- Garantizar código **limpio**, **seguro** y **mantenible**.
- Detectar errores y problemas antes de integrarlos en el repositorio.
- Automatizar la validación de calidad en cada commit.
- Asegurar una cobertura mínima de tests y validación robusta mediante pruebas de mutación.

---

## 🧩 Herramientas Integradas

| Herramienta | Propósito |
| --- | --- |
| ⚡ **ruff** | Linting y formateo rápido (reemplaza a `flake8`, `isort`, `black`). |
| 📘 **codespell** | Detección de errores tipográficos comunes. |
| 🚦 **xenon** | Evaluación de complejidad ciclomática del código. |
| 🔒 **bandit** | Análisis estático de seguridad del código Python. |
| 🧬 **Cosmic Ray** | Mutation Testing para validar la calidad real de los tests. |
| ✅ **pytest & pytest-cov** | Ejecución de tests unitarios e integración, con cobertura mínima garantizada (≥ 80%). |

---

## 📌 Hooks configurados

### ⚡ `ruff`

**Función:** Linting y formateo automático del código.

```bash
pipenv run ruff check src
pipenv run ruff format src
```

---

### 📘 `codespell`

**Función:** Detecta errores tipográficos comunes.

```bash
pipenv run codespell --ignore-words .codespell.ignorewords --skip=.venv

```

---

### 🚦 `xenon-complexity`

**Función:** Evalúa la complejidad ciclomática del código (máximo permitido: B).

```bash
pipenv run python -m xenon --max-absolute B --max-modules B --max-average B ./src
```

---

### 🔒 `bandit`

**Función:** Análisis estático para detectar problemas de seguridad.

```bash
pipenv run bandit -c .bandit.yml -r ./src
```

---

### 🧬 `mutation-testing`

**Función:** Realiza pruebas de mutación con `cosmic-ray`, garantizando tests efectivos.

- **Score mínimo requerido:** `80%`
- **Salida:** Genera reporte en `logs/mutating_testing_report.json` y `logs/cosmic_report.txt`.
- **Mutantes supervivientes:** Se documentan en `logs/survivors.md` (si existen).

```bash
pipenv run python scripts/mutation_check.py
```

**Resultados esperados:**

- ✅ **Al pasar:**

```
Mutation score: 87.5% (14/16 total mutants killed)
Mutation testing PASSED
```

- ❌ **Al fallar:**

```
Mutation score: 50.0% (3/6 total mutants killed)
--- Mutation testing FAILED: minimum 80.0%, obtained 50.0%
```

---

### ✅ `pytest coverage-check`

**Función:** Valida que la cobertura total de tests unitarios e integración sea ≥ 80%.

```bash
pipenv run pytest --cov=src --cov=agents --cov-fail-under=80
```

**Falla el commit si la cobertura es insuficiente.**

---

## 🚀 Ejecución global automática

Al ejecutar:

```bash
pipenv run pre-commit run --all-files 2>&1 | tee logs/precommit.log
```

Se realiza la validación integral del código, guardando un log completo de la ejecución en `logs/precommit.log`.

---

## 📂 Estructura de Archivos clave

| Archivo | Descripción |
| --- | --- |
| `.pre-commit-config.yaml` | Configuración centralizada de hooks pre-commit. |
| `pyproject.toml` | Gestión integrada de dependencias y herramientas. |
| `scripts/mutation_check.py` | Automatiza ejecución y reporte de Mutation Testing. |
| `config.toml` | Configuración para ejecución de `cosmic-ray`. |
| `cr_session.sqlite` | Base de datos generada por `cosmic-ray`. |
| `logs/*` | Reportes y logs generados por los hooks y scripts. |

---

## 📌 Recomendaciones finales

- 🔧 Ejecuta regularmente todos los hooks para mantener la calidad.
- 🔍 Revisa reportes generados (especialmente `survivors.md` de mutantes supervivientes).
- 🚩 No realices commit si alguno de los hooks falla, corrige primero los problemas detectados especialmente:
    - **Complejidad ciclomática** (`xenon`).
    - **Problemas de seguridad** (`bandit`).
    - **Mutantes supervivientes** en Mutation Testing.

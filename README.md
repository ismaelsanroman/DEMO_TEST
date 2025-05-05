
# 🤖 mock-agent-AI

Simulación de una arquitectura de microservicios para pruebas de un Agente de IA en el sector bancario. Este entorno permite testear flujos entre un orquestador y varios microservicios especialistas que responden a preguntas bancarias.

---

## 🧱 Estructura del proyecto

```
santander-simulator/
├── .venv/
│
├── mock_agent_ai/                      # Carpeta que agrupa todos los microservicios
│   ├── micro_consultas/
│   │   ├── __init__.py
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── micro_cuentas/
│   │   ├── __init__.py
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── micro_ia/
│   │   ├── __init__.py
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── micro_identidad/
│   │   ├── __init__.py
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   └── orquestador/
│       ├── __init__.py
│       ├── Dockerfile
│       ├── main.py
│       ├── requirements.txt
│       └── consultas_disponibles.md
│
├── docker-compose.yml
│
├── reports/                            # Resultados de pruebas Allure (unit + bdd)
│
├── tests/                              # Código de pruebas
│   ├── conftest.py
│   ├── pytest.ini
│   ├── features/
│   │   ├── behave.ini
│   │   ├── environment.py
│   │   ├── micro_orquestador.feature
│   │   ├── micro_consultas.feature
│   │   ├── micro_cuentas.feature
│   │   ├── micro_identidad.feature
│   │   ├── micro_ia.feature
│   │   └── steps/
│   │       ├── orquestador_steps.py
│   │       ├── consultas_steps.py
│   │       ├── cuentas_steps.py
│   │       ├── identidad_steps.py
│   │       └── ia_steps.py
│   └── unit/
│       ├── test_orquestador_unit.py
│       ├── test_consultas_unit.py
│       ├── test_cuentas_unit.py
│       ├── test_identidad_unit.py
│       └── test_ia_unit.py
│
├── Makefile
├── README.md
└── requirements.txt
```

Cada microservicio está construido con **FastAPI**, validación de token `Bearer`, y responde a peticiones HTTP POST en el endpoint `/respuesta`.

---

## ⚙️ Microservicios incluidos

| Microservicio     | Puerto | Función principal                                           |
| ----------------- | ------ | ----------------------------------------------------------- |
| `orquestador`     | 8000   | Orquesta peticiones y enruta al micro adecuado              |
| `micro_consultas` | 8001   | Devuelve movimientos, saldo, extractos, IBAN, etc.          |
| `micro_cuentas`   | 8002   | Simula apertura de cuentas, requisitos, tipos y condiciones |
| `micro_identidad` | 8003   | Verificación de identidad (DNI, 2FA, correo...)             |
| `micro_ia`        | 8004   | IA simulada con respuestas generales del banco              |

---

## 🚀 Cómo ejecutar sin Docker

```bash
cd mock-agent-AI/orquestador
uvicorn main:app --port 8000
```

Repite con los demás micros:

```bash
uvicorn main:app --port 8001  # micro_consultas
uvicorn main:app --port 8002  # micro_cuentas
uvicorn main:app --port 8003  # micro_identidad
uvicorn main:app --port 8004  # micro_ia
```

> Asegúrate de tener instalados los requisitos: `fastapi`, `uvicorn`, `httpx`

---

## 🐋 Cómo ejecutar con Podman

```bash
make start-mock
```

Esto:

* Elimina contenedores anteriores
* Construye los microservicios
* Levanta el entorno completo con `podman-compose`

> Accede al entorno desde: [http://localhost:8000](http://localhost:8000)

---

## 🔐 Autenticación

Todas las peticiones deben incluir el header:

```http
Authorization: Bearer secreto123
```

Puedes obtener un token con:

```bash
curl -X POST http://localhost:8000/token
```

---

## 🧪 Testing y reportes con Allure

El proyecto cuenta con tests automáticos y generación de reportes Allure tanto para:

- ✅ **Pruebas unitarias (pytest)** por microservicio
- 🧩 **Pruebas BDD (behave)** para simular flujos completos

### 🏷️ Organización por etiquetas

Cada test está etiquetado por:

- `@micro_orquestador`, `@micro_cuentas`, etc.
- `@bdd`, `@unit`
- `@smoke`, `@regression`
- Subfeatures como `@feature_token`, `@feature_respuestas`, etc.

Allure permite filtrar y agrupar por estos tags.

---

### ▶️ Ejecutar tests

```bash
# Unitarios
make test-unit

# BDD
make test-bdd
```

---

### 📊 Generar reportes Allure

```bash
# Reporte de unitarios
make unit-report

# Reporte de BDD
make behave-report

# Todo en uno
make full-report
```

Al ejecutarlo se abrirá automáticamente el navegador con el informe generado.

---

## 📌 Notas

* Este entorno está pensado para simular una arquitectura real en entorno controlado.
* Ideal para testear migraciones, trazabilidad, estrategias de testing y agentes IA con arquitectura distribuida.
* Incluye documentación Swagger por microservicio (`/docs`).
* Los reportes Allure se generan en `reports/` y se organizan por tipo (`unit` vs `bdd`).

---

*Ismael Sanromán — 2025*

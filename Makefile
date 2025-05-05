# Makefile para santander-simulator

# ─── Variables ────────────────────────────────────────────────────────────────
PROJECT        := santander-simulator
COMPOSE_FILE   := $(abspath mock_agent_ai/docker-compose.yml)
REPORT_DIR     := reports
UNIT_RESULTS   := $(REPORT_DIR)/unit_results
UNIT_REPORT    := $(REPORT_DIR)/unit_report
BDD_RESULTS    := $(REPORT_DIR)/behave_results
BDD_REPORT     := $(REPORT_DIR)/behave_report

# Ejecutables del entorno virtual
VENV_BIN       := .venv/bin
PYTEST         := $(VENV_BIN)/pytest
BEHAVE         := $(VENV_BIN)/behave
ALLURE         := allure  # Usa el global si no está en el venv

.PHONY: all start-mock stop-mock clean-network \
        test-unit test-bdd unit-report behave-report clean-reports full-report

# ─── Flujo por defecto ─────────────────────────────────────────────────────────
all: start-mock test-unit test-bdd

# ─── Mock Environment ──────────────────────────────────────────────────────────
clean-network:
	@echo "🧹 Limpiando red stale…"
	@podman network rm $(PROJECT)_default >/dev/null 2>&1 || true

start-mock: clean-network
	@echo "🚀 Iniciando entorno mock con Podman–Compose…"
	@podman-compose -f $(COMPOSE_FILE) -p $(PROJECT) down --remove-orphans --volumes
	@podman-compose -f $(COMPOSE_FILE) -p $(PROJECT) build
	@podman-compose -f $(COMPOSE_FILE) -p $(PROJECT) up -d
	@echo "🎉 Mock up en:"
	@echo "   • Orquestador → http://localhost:8000"
	@echo "   • Consultas   → http://localhost:8001"
	@echo "   • Cuentas     → http://localhost:8002"
	@echo "   • Identidad   → http://localhost:8003"
	@echo "   • IA          → http://localhost:8004"

stop-mock:
	@echo "🛑 Deteniendo entorno mock…"
	@podman-compose -f $(COMPOSE_FILE) -p $(PROJECT) down --remove-orphans --volumes

# ─── Tests ──────────────────────────────────────────────────────────────────────
test-unit:
	@echo "🧪 Ejecutando tests unitarios…"
	@$(PYTEST) tests/unit || true

test-bdd:
	@echo "📋 Ejecutando pruebas BDD…"
	@mkdir -p $(BDD_RESULTS)
	@$(BEHAVE) tests/features -f allure_behave.formatter:AllureFormatter -o $(BDD_RESULTS) || true

# ─── Reportes Allure ────────────────────────────────────────────────────────────
clean-reports:
	@echo "🗑 Limpiando carpeta de reportes…"
	@rm -rf $(REPORT_DIR)

unit-report: test-unit
	@echo "🔍 Generando reporte unitario…"
	@mkdir -p $(UNIT_RESULTS)
	@$(ALLURE) generate $(UNIT_RESULTS) -o $(UNIT_REPORT) --clean
	@$(ALLURE) open $(UNIT_REPORT)

behave-report: test-bdd
	@echo "🔍 Generando reporte BDD…"
	@mkdir -p $(BDD_RESULTS)
	@$(ALLURE) generate $(BDD_RESULTS) -o $(BDD_REPORT) --clean
	@$(ALLURE) open $(BDD_REPORT)

# ─── To-do en uno ────────────────────────────────────────────────────────────────
full-report: clean-reports test-unit test-bdd unit-report behave-report
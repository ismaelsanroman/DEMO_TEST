"""
Tests adicionales para aumentar la cobertura en casos límite
------------------------------------------------------------
Estos tests cubren:
* Saltar puertos ya reservados en `find_free_port`
* `launch_agents` cuando no hay recursos definidos
* Manejo de YAML inválido en `update_logic_config`
* Respuesta con JSON malformado en `send_instruction`
"""
import json
import yaml
import types
from types import SimpleNamespace

import pytest
import requests

from src.utils import utils
from src.resources import regards


# ---------------------------------------------------------------------
# find_free_port – salta puertos ya reservados
# ---------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.utils
# allure.feature("Gestión de puertos")
# allure.story("Evita puertos reservados")
def test_find_free_port_skips_already_reserved(monkeypatch):
    """Si el puerto inicial ya está reservado, debe devolver el siguiente libre."""
    utils.reserved_ports.clear()
    utils.reserved_ports.add(8000)  # forzamos reserva previa

    class _FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def connect_ex(self, addr):  # siempre devuelve libre
            return 1

    monkeypatch.setattr(utils.socket, "socket", lambda *a, **k: _FakeSocket())
    port = utils.find_free_port(start_port=8000, end_port=8002)
    assert port == 8001
    assert 8001 in utils.reserved_ports


# ---------------------------------------------------------------------
# launch_agents – sin recursos definidos
# ---------------------------------------------------------------------
class _DummyAgente:
    def __init__(self, nombre, rol="especialista", especialistas=None):
        self.nombre = nombre
        self.rol = rol
        self.especialistas = especialistas or []

    def dict(self):
        return {"nombre": self.nombre}


class _DummyManifest:
    def __init__(self):
        self.agentes = [_DummyAgente("foo")]
        self.resources = {}  # <-- sin recursos
        self.first_instruction = "hola"


@pytest.mark.unit
@pytest.mark.agents
# allure.feature("Lanzamiento de agentes")
# allure.story("Recursos no definidos")
def test_launch_agents_without_defined_resources(monkeypatch):
    """Comprueba que `write_resources` recibe {} cuando `manifest.resources` está vacío."""
    written_resources = []

    monkeypatch.setattr(
        regards,
        "write_resources",
        lambda _agente, resources, **__: written_resources.append(resources),
    )
    monkeypatch.setattr(regards, "find_free_port", lambda *_, **__: 8100)
    monkeypatch.setattr(regards, "launch_asgi_agent", lambda *_, **__: None)
    monkeypatch.setattr(regards, "update_logic_config", lambda *_, **__: None)

    resp = regards.launch_agents(_DummyManifest())
    assert resp["message"].startswith("Agentes lanzados")
    assert written_resources and all(r == {} for r in written_resources)


# ---------------------------------------------------------------------
# update_logic_config – fichero YAML corrupto
# ---------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.exception_handling
# allure.feature("Actualización de configuración")
# allure.story("Fallo al parsear YAML")
def test_update_logic_config_raises_on_invalid_yaml(monkeypatch, tmp_path, caplog):
    """Debe propagar el error y registrar el fallo cuando el YAML es inválido."""
    # Preparamos estructura de carpetas
    agent_name = "sup"
    cfg_path = tmp_path / agent_name / "src" / "agent"
    cfg_path.mkdir(parents=True)
    # Archivo con contenido dummy (no se usará porque safe_load se parchea)
    (cfg_path / "logic_config.yaml").write_text("dummy: true")

    # Forzamos que yaml.safe_load lance YAMLError
    def _boom(_):
        raise yaml.YAMLError("yaml corrupto")

    monkeypatch.setattr(utils.yaml, "safe_load", _boom)

    agente = {"nombre": agent_name}
    with caplog.at_level("ERROR"), pytest.raises(yaml.YAMLError):
        utils.update_logic_config(agente, especialistas=[], specialist_ports={}, base_path=str(tmp_path))

    assert "Error actualizando logic_config" in caplog.text


# ---------------------------------------------------------------------
# send_instruction – respuesta con JSON malformado
# ---------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.network
# allure.feature("Envío de instrucciones")
# allure.story("Respuesta JSON inválida")
def test_send_instruction_raises_on_bad_json(monkeypatch):
    """Si la respuesta del supervisor no contiene JSON válido debe propagarse el error."""

    class _BadJsonResp:
        status_code = 200

        @staticmethod
        def json():
            # Simulamos JSON malformado
            raise json.JSONDecodeError("Expecting value", "", 0)

    monkeypatch.setattr(requests, "post", lambda *a, **k: _BadJsonResp())

    with pytest.raises(json.JSONDecodeError):
        regards.send_instruction("haz algo")


# -------------------------

"""
Tests complementarios para validación robusta y casos E2E simulados
-------------------------------------------------------------------
Estos tests cubren:
* Simulación E2E: /launch_agents seguido de /instruction
* Simulación de KeyboardInterrupt
* YAML corrupto al cargar configuración
* Errores de permisos en escritura de archivos
"""
import json
import yaml
import pytest
import subprocess
import builtins
from types import SimpleNamespace
from fastapi.testclient import TestClient

from src.app.main import app
from src.utils import utils
from src.resources import regards


# ---------------------------------------------------------------------
# E2E simulado: /launch_agents + /instruction
# ---------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.e2e
# allure.feature("E2E Simulado")
# allure.story("Lanzamiento de agentes y envío de instrucción")
def test_e2e_launch_and_instruction(monkeypatch):
    client = TestClient(app)

    class DummyResponse:
        status_code = 200
        @staticmethod
        def json():
            return {"content": "respuesta del agente"}

    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: DummyResponse())

    manifest = {
        "agentes": [],
        "resources": {},
        "first_instruction": "Haz algo"
    }

    monkeypatch.setattr("src.resources.regards.write_resources", lambda *a, **k: None)
    monkeypatch.setattr("src.resources.regards.find_free_port", lambda: 8083)
    monkeypatch.setattr("src.resources.regards.launch_asgi_agent", lambda *a, **k: None)
    monkeypatch.setattr("src.resources.regards.update_logic_config", lambda *a, **k: None)

    response = client.post("/launch_agents", json=manifest)
    assert response.status_code == 200
    assert regards.runtime_status["status"] == "running"

    response = client.post("/instruction", json="Hola, agente")
    assert response.status_code == 200
    assert response.json()["response"] == "respuesta del agente"


# ---------------------------------------------------------------------
# KeyboardInterrupt simulado
# ---------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.exception_handling
# allure.feature("Manejo de procesos")
# allure.story("Interrupción por teclado")
def test_launch_asgi_agent_keyboard_interrupt(monkeypatch):
    def boom(*a, **k):
        raise KeyboardInterrupt("interrumpido")

    monkeypatch.setattr(subprocess, "Popen", boom)

    agente_stub = SimpleNamespace(nombre="interruptible")

    with pytest.raises(KeyboardInterrupt):
        utils.launch_asgi_agent(agente_stub, port=8080, base_path=".")


# ---------------------------------------------------------------------
# YAML corrupto al cargar config
# ---------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.exception_handling
# allure.feature("Configuración YAML")
# allure.story("Fichero corrupto")
def test_update_logic_config_invalid_yaml(monkeypatch, tmp_path):
    agente = {"nombre": "supervisor"}
    specialists = []
    ports = {}

    path = tmp_path / "supervisor" / "src" / "agent"
    path.mkdir(parents=True)
    config_path = path / "logic_config.yaml"
    config_path.write_text(":::esto no es yaml válido:::")

    def fake_open(path, mode="r", *_, **__):
        return open(config_path, mode)

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(utils.yaml, "safe_load", lambda f: (_ for _ in ()).throw(yaml.YAMLError("archivo corrupto")))

    with pytest.raises(Exception):
        utils.update_logic_config(agente, specialists, ports, base_path=str(tmp_path))


# ---------------------------------------------------------------------
# Error por falta de permisos en escritura
# ---------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.exception_handling
# allure.feature("Escritura de recursos")
# allure.story("Permisos denegados en carpeta")
def test_write_resources_permission_error(monkeypatch, tmp_path):
    agent_name = "agente1"
    path = tmp_path / agent_name
    path.mkdir(parents=True)

    agente = {"nombre": agent_name}
    resources = {"cpu": "1", "memoria": "1"}

    def fail_open(*args, **kwargs):
        raise PermissionError("sin permiso")

    monkeypatch.setattr(builtins, "open", fail_open)

    with pytest.raises(PermissionError):
        utils.write_resources(agente, resources, base_path=str(tmp_path))

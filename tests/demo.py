# tests/test_regards.py
# 🔧 tests/test_regards.py
import types
import pytest
from fastapi import HTTPException

from src.resources import regards          # módulo bajo prueba


# ---------- Stubs / helpers ----------
class _DummyAgente:
    """Stub minimal de Agente con lo justo para los tests."""
    def __init__(self, nombre, rol="especialista", especialistas=None):
        self.nombre = nombre
        self.rol = rol
        self.especialistas = especialistas or []

    # el código llama a .dict() en varias ocasiones
    def dict(self):
        return {"nombre": self.nombre}


class _DummyManifest:
    def __init__(self, agentes):
        self.agentes = agentes
        self.resources = {}          # ningún recurso concreto
        self.first_instruction = "¡Hola, mundo!"


# ---------- Tests launch_agents ----------
@pytest.mark.unit
@pytest.mark.logic
def test_launch_agents_success(monkeypatch):
    """✅ Verifica que se lanzan todos los agentes y el estado pasa a 'running'."""
    calls = {"write": 0, "free_port": 0, "asgi": 0, "update": 0}

    monkeypatch.setattr(regards, "write_resources",
                        lambda *a, **k: calls.update(write=calls["write"] + 1))
    monkeypatch.setattr(regards, "find_free_port",
                        lambda *a, **k: [_ for _ in (8100, 8101, 8102)][calls["free_port"]])
    monkeypatch.setattr(regards, "launch_asgi_agent",
                        lambda *a, **k: calls.update(asgi=calls["asgi"] + 1))
    monkeypatch.setattr(regards, "update_logic_config",
                        lambda *a, **k: calls.update(update=calls["update"] + 1))

    agentes = [_DummyAgente("foo"), _DummyAgente("bar", rol="orquestador")]
    manifest = _DummyManifest(agentes)
    resp = regards.launch_agents(manifest)

    assert regards.runtime_status["status"] == "running"
    assert "Agentes" in resp["message"]          # copia literal del código original
    assert calls["asgi"] == 3                    # 2 especialistas + 1 orquestador general


@pytest.mark.unit
@pytest.mark.exception_handling
def test_launch_agents_handles_exception(monkeypatch):
    """💥 Simula fallo y comprueba que se invoca kill_all_agents y se propaga HTTPException."""
    monkeypatch.setattr(regards, "write_resources", lambda *a, **k: None)
    monkeypatch.setattr(regards, "find_free_port", lambda *a, **k: 8100)
    monkeypatch.setattr(regards, "update_logic_config", lambda *a, **k: None)

    # 👉 Provocamos el error aquí
    def _boom(*_, **__):
        raise RuntimeError("kaputt")
    monkeypatch.setattr(regards, "launch_asgi_agent", _boom)

    killed = {"called": False}
    monkeypatch.setattr(regards, "kill_all_agents",
                        lambda: killed.update(called=True))

    with pytest.raises(HTTPException):
        regards.launch_agents(_DummyManifest([_DummyAgente("foo")]))

    assert killed["called"] is True


# ---------- Tests kill_agents & status ----------
@pytest.mark.unit
def test_kill_agents_success(monkeypatch):
    called = {"kill": False}
    monkeypatch.setattr(regards, "kill_all_agents",
                        lambda: called.update(kill=True))
    regards.runtime_status["status"] = "running"     # pre-condición
    resp = regards.kill_agents()

    assert called["kill"]
    assert regards.runtime_status["status"] == "stopped"
    assert resp["message"].startswith("Todos los agentes")


@pytest.mark.unit
def test_get_status_returns_runtime_status():
    regards.runtime_status.update(status="running", foo="bar")
    assert regards.get_status() == regards.runtime_status


# ---------- Tests send_instruction ----------
class _DummyRespOK:
    status_code = 200

    @staticmethod
    def json():
        return {"content": "🛰️ Todo en orden"}

class _DummyRespFail:
    status_code = 500

    @staticmethod
    def json():
        return {"error": "bad things happened"}

@pytest.mark.unit
@pytest.mark.network
def test_send_instruction_success(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda *_, **__: _DummyRespOK())

    resp = regards.send_instruction("haz algo")
    assert resp["status"] == "sent"
    assert "haz algo" in resp["instruction"]

@pytest.mark.unit
@pytest.mark.exception_handling
def test_send_instruction_connection_error(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post",
                        lambda *_, **__: (_ for _ in ()).throw(requests.exceptions.ConnectionError))

    resp = regards.send_instruction("otro intento")
    assert "error" in resp



# tests/test_utils.py
# 🛠️ tests/test_utils.py
import io
import types
import pytest

from src.utils import utils


# ---------- find_free_port ----------
class _FakeSocket:
    """Socket minimal para emular connect_ex."""
    def __init__(self, *_, **__):
        self._closed = False

    def __enter__(self):  # soporta with
        return self

    def __exit__(self, *exc):
        self._closed = True

    def connect_ex(self, addr):
        host, port = addr
        # puerto 8000 libre (devuelve 1), resto ocupado (0)
        return 1 if port == 8000 else 0


@pytest.mark.unit
def test_find_free_port_returns_available_port(monkeypatch):
    monkeypatch.setattr(utils.socket, "socket", lambda *a, **k: _FakeSocket())
    port = utils.find_free_port(8000, 8003)
    assert port == 8000
    assert port in utils.reserved_ports


@pytest.mark.unit
@pytest.mark.exception_handling
def test_find_free_port_raises_error_when_full(monkeypatch):
    # todos los puertos "ocupados" -> connect_ex devuelve 0 siempre
    class _BusySocket(_FakeSocket):
        def connect_ex(self, _addr):  # pylint: disable=arguments-differ
            return 0
    monkeypatch.setattr(utils.socket, "socket", lambda *a, **k: _BusySocket())
    with pytest.raises(RuntimeError):
        utils.find_free_port(8000, 8002)


# ---------- launch_process_agent ----------
class _DummyPopen:
    def __init__(self, *_, **__):
        self.killed = False

    def kill(self):
        self.killed = True

@pytest.mark.unit
def test_launch_process_agent_creates_folders_and_starts_process(monkeypatch, tmp_path):
    made_dirs = []

    monkeypatch.setattr(utils.os, "makedirs",
                        lambda path, exist_ok=True: made_dirs.append(path))
    monkeypatch.setattr(utils.subprocess, "Popen", lambda *_, **__: _DummyPopen())

    agente = {
        "nombre": "super-proc",
        "resources": {
            "input_folder": tmp_path / "in",
            "output_folder": tmp_path / "out"
        }
    }
    utils.launch_process_agent(agente, base_path=str(tmp_path))
    assert made_dirs                                  # se han creado carpetas
    assert "super-proc" in utils.processes            # registro en el diccionario


@pytest.mark.unit
@pytest.mark.exception_handling
def test_launch_process_agent_logs_error_on_failure(monkeypatch, caplog):
    def _boom(*_, **__):
        raise RuntimeError("no hay quien lance esto")
    monkeypatch.setattr(utils.subprocess, "Popen", _boom)

    agente = {"nombre": "fallon", "resources": {"input_folder": "x", "output_folder": "y"}}
    with pytest.raises(RuntimeError):
        utils.launch_process_agent(agente)
    # se registró en el log
    assert any("Error lanzando proceso agente" in rec.message for rec in caplog.records)


# ---------- launch_asgi_agent ----------
@pytest.mark.unit
def test_launch_asgi_agent_starts_uvicorn_process(monkeypatch):
    popen_calls = {}

    def _fake_popen(cmd, cwd):
        popen_calls["cmd"] = cmd
        popen_calls["cwd"] = cwd
        return _DummyPopen()
    monkeypatch.setattr(utils.subprocess, "Popen", _fake_popen)

    agente_stub = types.SimpleNamespace(nombre="api-agent")
    utils.launch_asgi_agent(agente_stub, port=8555, base_path="/tmp")
    assert "uvicorn" in popen_calls["cmd"][0]
    assert popen_calls["cwd"].endswith("api-agent")


# ---------- write_resources ----------
@pytest.mark.unit
def test_write_resources_creates_json_file(monkeypatch, tmp_path):
    fake_file = io.StringIO()

    def _mock_open(*_, **__):
        fake_file.seek(0)
        return fake_file
    monkeypatch.setattr(utils, "open", _mock_open, raising=True)
    monkeypatch.setattr(utils.json, "dump", lambda data, f: f.write("{}"))

    utils.write_resources({"nombre": "x"}, {}, base_path=str(tmp_path))
    fake_file.seek(0)
    assert fake_file.read() == "{}"                   # JSON escrito


@pytest.mark.unit
@pytest.mark.exception_handling
def test_write_resources_handles_write_error(monkeypatch):
    def _boom(*_, **__):
        raise IOError("disk is full")
    monkeypatch.setattr(utils, "open", _boom, raising=True)

    with pytest.raises(IOError):
        utils.write_resources({"nombre": "y"}, {})


# ---------- update_logic_config ----------
@pytest.mark.unit
def test_update_logic_config_updates_yaml_correctly(monkeypatch, tmp_path):
    read_yaml = {"description": "dummy"}
    dumped_cfg = {}

    # mock de open que devuelva un StringIO para lectura y otro para escritura
    def _mock_open(path, mode="r", *_, **__):
        if "r" in mode:
            return io.StringIO("description: dummy")
        return io.StringIO()          # escritura

    monkeypatch.setattr(utils, "open", _mock_open, raising=True)
    monkeypatch.setattr(utils.yaml, "safe_load", lambda _: read_yaml)
    monkeypatch.setattr(utils.yaml, "safe_dump",
                        lambda data, _file: dumped_cfg.update(data))

    utils.update_logic_config(
        agente={"nombre": "sup"}, especialistas=[],
        specialist_ports={}, base_path=str(tmp_path)
    )
    # la clave supervisedAgents aparece en la salida
    assert "supervisedAgents" in dumped_cfg


# ---------- kill_all_agents ----------
@pytest.mark.unit
def test_kill_all_agents_stops_all_processes(monkeypatch):
    proc_a = _DummyPopen()
    proc_b = _DummyPopen()
    utils.processes.clear()
    utils.processes.update(a=proc_a, b=proc_b)

    utils.kill_all_agents()
    assert not utils.processes                   # dict vacío
    assert proc_a.killed and proc_b.killed       # ambos procesos .kill() llamado

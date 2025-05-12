
import pytest

@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.functional
# @allure.feature("Agents")
# @allure.story("Launch Logic")
def test_launch_agents_success(monkeypatch):
    """✅ Verifica que se lanzan todos los agentes y el estado pasa a 'running'."""

    calls = {
        "write": 0,
        "free_port": 0,
        "asgi": 0,
        "update": 0,
        "nombres_lanzados": [],
    }

    monkeypatch.setattr(regards, "write_resources", lambda *a, **k: calls.update(write=calls["write"] + 1))

    monkeypatch.setattr(regards, "find_free_port", lambda *a, **k: [p for p in (8100, 8101, 8102)][calls["free_port"]])

    def fake_launch_asgi_agent(*args, nombre=None, **kwargs):
        # Aseguramos que siempre obtenemos un nombre válido
        nombre_real = nombre or getattr(args[0], "nombre", None) or str(args[0])
        calls["asgi"] += 1
        calls["nombres_lanzados"].append(nombre_real)

    monkeypatch.setattr(regards, "launch_asgi_agent", fake_launch_asgi_agent)

    monkeypatch.setattr(regards, "update_logic_config", lambda *a, **k: calls.update(update=calls["update"] + 1))

    agentes = [
        _DummyAgente("foo"),
        _DummyAgente(nombre="bar", rol="orquestador"),
        _DummyAgente("baz"),
    ]
    manifest = _DummyManifest(agentes)

    resp = regards.launch_agents(manifest)

    # ✅ Comprobaciones
    assert regards.runtime_status["status"] == "running"
    assert "Agentes" in resp["message"]
    assert calls["asgi"] == 3, f"Se esperaban 3 lanzamientos, pero se hicieron {calls['asgi']}"
    assert "bar" in calls["nombres_lanzados"], "❌ El agente con rol 'orquestador' no fue lanzado correctamente"

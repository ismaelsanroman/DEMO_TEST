def test_launch_agents_success(monkeypatch):
    """✅ Verifica que se lanzan todos los agentes y el estado pasa a 'running'. También se comprueba que el 'orquestador' no se ignora."""
    calls = {
        "write": 0,
        "free_port": 0,
        "asgi": 0,
        "update": 0,
        "nombres_lanzados": []
    }

    monkeypatch.setattr(regards, "write_resources", lambda *a, **k: calls.update(write=calls["write"] + 1))
    monkeypatch.setattr(regards, "find_free_port", lambda *a, **k: [p for p in (8100, 8101, 8102)][calls["free_port"]])
    monkeypatch.setattr(
        regards,
        "launch_asgi_agent",
        lambda *a, nombre=None, **k: calls.update(
            asgi=calls["asgi"] + 1,
            nombres_lanzados=calls["nombres_lanzados"] + [nombre]
        )
    )
    monkeypatch.setattr(regards, "update_logic_config", lambda *a, **k: calls.update(update=calls["update"] + 1))

    agentes = [
        _DummyAgente("foo"),
        _DummyAgente(nombre="bar", rol="orquestador"),
        _DummyAgente("baz"),
    ]
    manifest = _DummyManifest(agentes)

    resp = regards.launch_agents(manifest)

    assert regards.runtime_status["status"] == "running"
    assert "Agentes" in resp["message"]
    assert calls["asgi"] == 3

    # 💀 Aquí matamos al mutante:
    assert "bar" in calls["nombres_lanzados"], "El agente con rol 'orquestador' no fue lanzado"


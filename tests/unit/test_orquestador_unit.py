# tests/unit/test_orquestador_unit.py

import pytest
import allure
from fastapi.testclient import TestClient
from mock_agent_ai.orquestador.main import app, VALID_TOKEN

client = TestClient(app)

@allure.tag("micro:orquestador", "tipo:unitario")
@allure.feature("Microservicio Orquestador")
@allure.story("Obtener token")
@pytest.mark.unit
@pytest.mark.micro_orquestador
def test_obtener_token():
    """Comprueba que POST /token devuelve un access_token válido."""
    resp = client.post("/token")
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["access_token"] == VALID_TOKEN

# tests/unit/test_consultas_unit.py

import pytest
import allure
from mock_agent_ai.micro_consultas.main import responder, Pregunta

@allure.tag("micro:consultas", "tipo:unitario")
@allure.feature("Microservicio Consultas")
@allure.story("Respuesta de saldo")
@pytest.mark.unit
@pytest.mark.micro_consultas
@pytest.mark.asyncio
async def test_responder_saldo():
    """Si la pregunta contiene 'saldo', devuelve el saldo correcto."""
    pregunta = Pregunta(pregunta="¿Cuál es mi saldo actual?")
    resultado = await responder(pregunta)
    assert resultado == {"respuesta": "Tu saldo actual es de 1.275,45€."}

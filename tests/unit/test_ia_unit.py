# tests/unit/test_ia_unit.py

import pytest
import allure
from mock_agent_ai.micro_ia.main import responder, Pregunta

@allure.tag("micro:ia", "tipo:unitario")
@allure.feature("Microservicio IA")
@allure.story("Respuesta de hipoteca")
@pytest.mark.unit
@pytest.mark.micro_ia
@pytest.mark.asyncio
async def test_responder_hipoteca():
    """Si la pregunta contiene 'hipoteca', devuelve el tipo de interés."""
    pregunta = Pregunta(pregunta="¿Qué tipo de interés tienen las hipotecas?")
    resultado = await responder(pregunta)
    assert resultado == {"respuesta": "Actualmente el tipo de interés para hipotecas es del 3,2%."}

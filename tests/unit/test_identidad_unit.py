# tests/unit/test_identidad_unit.py

import pytest
import allure
from mock_agent_ai.micro_identidad.main import responder, Pregunta

@allure.tag("micro:identidad", "tipo:unitario")
@allure.feature("Microservicio Identidad")
@allure.story("Verificación de DNI")
@pytest.mark.unit
@pytest.mark.micro_identidad
@pytest.mark.asyncio
async def test_responder_verificar_dni():
    """Si la pregunta contiene 'DNI', valida el documento correctamente."""
    pregunta = Pregunta(pregunta="¿Puedes verificar mi DNI?")
    resultado = await responder(pregunta)
    assert resultado == {
        "respuesta": "Tu documento ha sido validado correctamente. Coincide con nuestros registros."
    }

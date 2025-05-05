# tests/unit/test_cuentas_unit.py

import pytest
import allure
from mock_agent_ai.micro_cuentas.main import responder, Pregunta

@allure.tag("micro:cuentas", "tipo:unitario")
@allure.feature("Microservicio Cuentas")
@allure.story("Apertura de cuenta")
@pytest.mark.unit
@pytest.mark.micro_cuentas
@pytest.mark.asyncio
async def test_responder_abrir_cuenta():
    """Si la pregunta contiene 'abrir cuenta', devuelve confirmación de apertura."""
    pregunta = Pregunta(pregunta="Quiero abrir cuenta")
    resultado = await responder(pregunta)
    assert resultado == {
        "respuesta": "Tu cuenta ha sido abierta correctamente con IBAN ES6600190020961234567890."
    }

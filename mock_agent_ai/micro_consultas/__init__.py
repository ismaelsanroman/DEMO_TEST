# mock_agent_ai/micro_consultas/__init__.py

"""
Microservicio Consultas.
Gestiona la lógica de consulta de movimientos, saldo, extractos, IBAN, cajeros, ingresos, tarjetas y tipo de cambio.
"""

from .main import Pregunta, responder

__all__ = [
    "Pregunta",
    "responder",
]

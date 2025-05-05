# mock_agent_ai/micro_cuentas/__init__.py

"""
Microservicio Cuentas.
Gestiona la apertura de cuentas, consulta de comisiones, requisitos y plazos de apertura.
"""

from .main import Pregunta, responder

__all__ = [
    "Pregunta",
    "responder",
]

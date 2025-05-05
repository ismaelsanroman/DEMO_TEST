# mock_agent_ai/micro_identidad/__init__.py

"""
Microservicio Identidad.
Provee lógica para verificar la identidad del usuario mediante DNI, SMS, correo y 2FA.
"""

from .main import Pregunta, responder

__all__ = [
    "Pregunta",
    "responder",
]

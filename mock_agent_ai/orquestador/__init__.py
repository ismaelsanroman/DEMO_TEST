# mock_agent_ai/orquestador/__init__.py

"""
Microservicio Orquestador.
Encargado de autenticar solicitudes y enrutar preguntas
a los distintos microservicios (consultas, cuentas, identidad, IA).
"""

from .main import app, VALID_TOKEN, MICROS

__all__ = [
    "app",
    "VALID_TOKEN",
    "MICROS",
]

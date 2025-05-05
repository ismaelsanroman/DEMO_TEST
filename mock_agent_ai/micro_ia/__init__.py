# mock_agent_ai/micro_ia/__init__.py

"""
Microservicio IA.
Provee respuestas automáticas basadas en palabras clave para servicios financieros.
"""

from .main import Pregunta, responder, RESPUESTAS_IA

__all__ = [
    "Pregunta",
    "responder",
    "RESPUESTAS_IA",
]

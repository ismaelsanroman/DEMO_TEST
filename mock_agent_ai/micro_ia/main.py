# mock-agent-AI/micro_ia/main.py

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import logging

app = FastAPI(
    title="🤖 Microservicio de IA",
    description="Simula una IA bancaria que responde a preguntas generales del usuario.",
    version="1.1.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("micro_ia")

VALID_TOKEN = "secreto123"

class Pregunta(BaseModel):
    pregunta: str

    class Config:
        json_schema_extra = {
            "example": {
                "pregunta": "¿Qué tipo de interés tiene la hipoteca?"
            }
        }

# Base de conocimientos simulada
RESPUESTAS_IA = {
    "hipoteca": "Actualmente el tipo de interés para hipotecas es del 3,2%.",
    "tarjeta": "Puedes solicitar una tarjeta desde la app o acudiendo a una oficina.",
    "transferencia": "Una transferencia nacional tarda aproximadamente 24h hábiles.",
    "comisión": "La comisión de mantenimiento es de 10€ trimestrales, pero puede eliminarse cumpliendo ciertos requisitos.",
    "oficina": "Nuestro horario de atención en oficinas es de lunes a viernes de 8:30 a 14:00.",
    "certificado": "Puedes descargar tu certificado de titularidad bancaria desde la app o el área de cliente web.",
    "préstamo": "Ofrecemos préstamos personales desde un 5,5% TIN con aprobación rápida online.",
    "inversión": "Contamos con planes de inversión adaptados a tu perfil de riesgo, consulta con tu asesor."
}

@app.middleware("http")
async def validar_token(request: Request, call_next):
    rutas_publicas = ["/token", "/docs", "/openapi.json"]
    if any(request.url.path.startswith(r) for r in rutas_publicas):
        return await call_next(request)

    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Token inválido o no proporcionado")

    return await call_next(request)

@app.post("/respuesta", tags=["🧠 IA Bancaria"], summary="Consulta general a la IA")
async def responder(pregunta: Pregunta):
    """
    Devuelve una respuesta simulada según la palabra clave detectada en la pregunta.

    Palabras clave soportadas:
    - hipoteca
    - tarjeta
    - transferencia
    - comisión
    - oficina
    - certificado
    - préstamo
    - inversión

    Si no se encuentra ninguna coincidencia, responde con un mensaje genérico.
    """
    texto = pregunta.pregunta.lower()
    logger.info(f"[IA] Pregunta recibida: {texto}")

    for clave, respuesta in RESPUESTAS_IA.items():
        if clave in texto:
            return {"respuesta": respuesta}

    return {"respuesta": "Lo siento, no tengo información sobre eso en este momento."}

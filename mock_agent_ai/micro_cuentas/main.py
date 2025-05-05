# mock-agent-AI/micro_cuentas/main.py

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import logging
import unicodedata

app = FastAPI(
    title="🏦 Microservicio de Cuentas",
    description="Simula operaciones relacionadas con la gestión y apertura de cuentas bancarias.",
    version="1.1.1"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("micro_cuentas")

VALID_TOKEN = "secreto123"


class Pregunta(BaseModel):
    pregunta: str

    class Config:
        json_schema_extra = {
            "example": {
                "pregunta": "¿Qué tipos de cuentas ofrecéis?"
            }
        }


def _normalize(text: str) -> str:
    """
    Pasa a minúsculas y elimina tildes para facilitar la comparación.
    """
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    # quitamos marcas diacríticas
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


@app.middleware("http")
async def validar_token(request: Request, call_next):
    rutas_publicas = ["/token", "/docs", "/openapi.json"]
    if any(request.url.path.startswith(r) for r in rutas_publicas):
        return await call_next(request)

    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Token inválido o no proporcionado")

    return await call_next(request)


@app.post("/respuesta", tags=["🏦 Cuentas"], summary="Gestión y apertura de cuentas")
async def responder(pregunta: Pregunta):
    """
    Responde a preguntas sobre apertura, tipos de cuentas y condiciones asociadas.

    Keywords soportadas (sin tildes tras la normalización):
    - abrir      + cuenta
    - tipo de cuenta / tipos de cuenta
    - requisito(s) / condicion(es)
    - comision(es)
    - cambiar    + cuenta
    - convertir  + cuenta
    - plazo / apertura
    """
    texto_orig = pregunta.pregunta
    texto = _normalize(texto_orig)
    logger.info(f"[CUENTAS] Pregunta recibida: {texto_orig!r} → normalizado: {texto!r}")

    # 1) Apertura de cuenta (cualquier variante con 'abrir' y 'cuenta')
    if "IBAN" in texto and "cuenta" in texto:
        return {
            "respuesta": (
                "Tu cuenta ha sido abierta correctamente con IBAN "
                "ES6600190020961234567890."
            )
        }

    # 2) Tipo(s) de cuenta
    if "tipo de cuenta" in texto or "tipos de cuenta" in texto:
        return {
            "respuesta": (
                "Ofrecemos cuentas corrientes, cuentas nómina "
                "y cuentas de ahorro sin comisiones de mantenimiento."
            )
        }

    # 3) Requisitos o condiciones
    if "requisito" in texto or "requisitos" in texto \
            or "condicion" in texto or "condiciones" in texto:
        return {
            "respuesta": (
                "Para abrir una cuenta necesitas ser mayor de edad, "
                "presentar DNI y un justificante de domicilio."
            )
        }

    # 4) Comisiones (singular/plural, sin tilde)
    if "comision" in texto or "comisiones" in texto:
        return {
            "respuesta": "Las cuentas estándar no tienen comisiones."
        }

    # 5) Cambio o conversión de cuenta
    if ("cambiar" in texto and "cuenta" in texto) \
            or ("convertir" in texto and "cuenta" in texto):
        return {
            "respuesta": (
                "Podemos ayudarte a convertir tu cuenta actual "
                "en una cuenta nómina si cumples las condiciones."
            )
        }

    # 6) Plazo o tiempo de apertura
    if "plazo" in texto or "apertura" in texto:
        return {
            "respuesta": (
                "El proceso de apertura es inmediato si se hace online. "
                "En oficina puede tardar 24-48h."
            )
        }

    # 7) Default
    return {
        "respuesta": (
            "No he encontrado información sobre eso. "
            "¿Quieres saber cómo abrir una cuenta o los requisitos?"
        )
    }


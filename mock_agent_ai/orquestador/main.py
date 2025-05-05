# mock-agent-AI/orquestador/main.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
import os
import logging

app = FastAPI(
    title="🧠 Orquestador del Agente IA Bancario",
    description="Servicio que enruta preguntas bancarias a los microservicios adecuados: consultas, cuentas, identidad e inteligencia artificial.",
    version="1.0.1",
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orquestador")

# Endpoints de los micros (por orden esperado: consultas, cuentas, identidad, IA)
MICROS = os.getenv("MICROS_ENDPOINTS", "").split(",")

# Token simulado
VALID_TOKEN = "secreto123"

class Consulta(BaseModel):
    pregunta: str

    class Config:
        json_schema_extra = {
            "example": {
                "pregunta": "¿Cuál fue mi último movimiento bancario?"
            }
        }

@app.post("/token", tags=["🔐 Auth"], summary="Obtener token de autenticación")
async def obtener_token():
    """
    Devuelve un token de acceso simulado para autenticar las peticiones.
    """
    return JSONResponse(content={"access_token": VALID_TOKEN, "token_type": "bearer"})

@app.middleware("http")
async def validar_token(request: Request, call_next):
    rutas_publicas = ["/token", "/docs", "/openapi.json"]
    if any(request.url.path.startswith(r) for r in rutas_publicas):
        return await call_next(request)

    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Token inválido o no proporcionado")

    return await call_next(request)

@app.post("/consulta", tags=["🧭 Consulta Bancaria"], summary="Procesar consulta bancaria")
async def procesar_consulta(consulta: Consulta):
    """
    Determina el microservicio adecuado según la pregunta del usuario
    y reenvía la consulta para obtener una respuesta.

    Microservicios:
    - 📊 Consultas: movimiento, saldo, extracto, recibo, IBAN, cajero, ingreso, tarjeta, divisa, seguridad
    - 🏦 Cuentas: abrir cuenta, tipos, requisitos, comisiones, cambiar tipo, tiempo
    - 🆔 Identidad: DNI, SMS, correo, doble factor, verificación
    - 🤖 IA: cualquier otra pregunta general
    """
    texto = consulta.pregunta.lower()
    logger.info(f"Pregunta recibida: {texto}")

    # Añadimos sinónimos y frases comunes para mejorar el enrutado
    if any(palabra in texto for palabra in [
        "movimiento", "saldo", "extracto", "recibo", "luz", "agua", "internet",
        "iban", "cajero", "oficina", "ingreso", "tarjeta", "límite",
        "divisa", "cambio", "seguridad", "acceso", "comprado", "compra", "últimamente"
    ]):
        micro_url = MICROS[0]  # micro_consultas
    elif any(palabra in texto for palabra in [
        "abrir cuenta", "cuenta nueva", "tipo de cuenta", "tipos de cuenta",
        "requisito", "documentación", "comisión", "cambiar cuenta", "convertir cuenta", "plazo", "tiempo"
    ]):
        micro_url = MICROS[1]  # micro_cuentas
    elif any(palabra in texto for palabra in [
        "dni", "nie", "sms", "código", "correo", "email", "2fa",
        "verificar identidad", "autenticación", "doble factor", "identidad"
    ]):
        micro_url = MICROS[2]  # micro_identidad
    else:
        micro_url = MICROS[3]  # micro_ia

    logger.info(f"Reenviando consulta a: {micro_url}/respuesta")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{micro_url}/respuesta",
                json={"pregunta": texto},
                headers={"Authorization": f"Bearer {VALID_TOKEN}"}
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error al comunicar con {micro_url}: {e}")
            raise HTTPException(status_code=502, detail="Error al contactar con microservicio")

    return {"respuesta": response.json().get("respuesta", "Sin respuesta")}

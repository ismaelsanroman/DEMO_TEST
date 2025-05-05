# mock-agent-AI/micro_consultas/main.py

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import logging

app = FastAPI(
    title="📊 Microservicio de Consultas",
    description="Responde preguntas sobre movimientos, saldo, extractos, recibos y más.",
    version="1.1.1",  # 🔄 Versión actualizada
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("micro_consultas")

VALID_TOKEN = "secreto123"

class Pregunta(BaseModel):
    pregunta: str

    class Config:
        json_schema_extra = {
            "example": {
                "pregunta": "¿Cuál es el límite de mi tarjeta?"
            }
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

@app.post("/respuesta", tags=["📊 Consultas"], summary="Consultar información bancaria")
async def responder(pregunta: Pregunta):
    """
    Responde a preguntas relacionadas con movimientos, saldo, recibos, tarjetas y más.

    **Requiere token válido**
    """
    texto = pregunta.pregunta.lower()
    logger.info(f"[CONSULTAS] Recibida pregunta: {texto}")

    if any(p in texto for p in ["movimiento", "compra", "comprado", "últimamente"]):
        return {"respuesta": "Tu último movimiento fue una compra de 35€ en Amazon."}
    elif "saldo" in texto:
        return {"respuesta": "Tu saldo actual es de 1.275,45€."}
    elif "extracto" in texto:
        return {"respuesta": "Tu extracto de abril incluye 18 movimientos por un total de 1.052€."}
    elif any(p in texto for p in ["recibo", "luz", "agua", "internet"]):
        return {"respuesta": "Tu último recibo de internet fue de 44,90€ y se cargó el día 3 de este mes."}
    elif "iban" in texto:
        return {"respuesta": "Tu IBAN es ES6600190020961234567890."}
    elif any(p in texto for p in ["cajero", "oficina", "localizar"]):
        return {"respuesta": "Puedes encontrar la oficina o cajero más cercano en nuestra app, sección 'Dónde estamos'."}
    elif any(p in texto for p in ["ingreso", "entrada de dinero"]):
        return {"respuesta": "Recibiste un ingreso de 1.200€ el pasado 27 de abril."}
    elif any(p in texto for p in ["límite", "tarjeta"]):
        return {"respuesta": "El límite de tu tarjeta actual es de 2.000€ mensuales."}
    elif any(p in texto for p in ["divisa", "cambio"]):
        return {"respuesta": "El tipo de cambio actual EUR/USD es 1,09."}
    elif any(p in texto for p in ["último acceso", "seguridad"]):
        return {"respuesta": "Tu último acceso fue el 2 de mayo a las 17:42 desde la app móvil."}
    else:
        return {"respuesta": "No tengo información suficiente para responder a tu consulta específica."}

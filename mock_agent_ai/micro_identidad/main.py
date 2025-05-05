# mock-agent-AI/micro_identidad/main.py

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import logging

app = FastAPI(
    title="🆔 Microservicio de Identidad",
    description="Valida la identidad de usuarios en el contexto bancario simulado.",
    version="1.0.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("micro_identidad")

VALID_TOKEN = "secreto123"


class Pregunta(BaseModel):
    pregunta: str

    class Config:
        json_schema_extra = {
            "example": {
                "pregunta": "¿Puedes verificar mi identidad con mi DNI?"
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


@app.post("/respuesta", tags=["🧾 Identidad"], summary="Verificar identidad del usuario")
async def responder(pregunta: Pregunta):
    """
    Responde a solicitudes de verificación de identidad, incluyendo:
    - DNI/NIE
    - Código de SMS
    - Correo electrónico
    - Autenticación de dos factores

    **Requiere token válido**
    """
    texto = pregunta.pregunta.lower()
    logger.info(f"[IDENTIDAD] Pregunta recibida: {texto}")

    if "dni" in texto or "nie" in texto:
        return {"respuesta": "Tu documento ha sido validado correctamente. Coincide con nuestros registros."}
    elif "sms" in texto or "código" in texto or "llamada" in texto:
        return {"respuesta": "Código verificado correctamente. Tu sesión es segura."}
    elif "correo" in texto or "email" in texto:
        return {"respuesta": "Tu correo ha sido confirmado. Ya puedes continuar con tu operación."}
    elif "dos factores" in texto or "2fa" in texto:
        return {"respuesta": "Autenticación en dos pasos completada correctamente."}
    elif "verificar identidad" in texto or "identidad" in texto:
        return {"respuesta": "Identidad verificada con éxito para el usuario Juan Pérez."}
    else:
        return {"respuesta": "No se ha podido determinar el tipo de verificación. Por favor, especifica el método (DNI, SMS, correo...)."}

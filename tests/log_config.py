# tests/log_config.py

from loguru import logger
import os
import sys
from datetime import datetime

# 📁 Directorio donde guardar los logs
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# 🕒 Timestamp único por ejecución (fecha y hora hasta segundos)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE_PATH = os.path.join(LOGS_DIR, f"tests_{timestamp}.log")

# 🔁 Configuración de loguru
logger.remove()  # Elimina el handler por defecto (stdout)

# ➕ Salida a consola (colorida, info a partir de INFO)
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>[{time:HH:mm:ss}]</green> <level>[{level}]</level> <cyan>{message}</cyan>"
)

# 🧾 Salida a fichero (detallada, incluye DEBUG y trazas)
logger.add(
    LOG_FILE_PATH,
    level="DEBUG",
    rotation="1 day",  # Rota cada día
    retention="7 days",  # Mantiene logs por 7 días
    compression="zip",  # Comprime logs antiguos
    format="[{time:YYYY-MM-DD HH:mm:ss}] [{level}] {message}",
    backtrace=True,  # Añade traceback si hay excepciones
    diagnose=True  # Información útil de errores complejos
)


# 📤 Función auxiliar para recuperar la ruta del log actual
def get_log_file():
    return LOG_FILE_PATH

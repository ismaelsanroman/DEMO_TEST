# orquestador/Dockerfile
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expone el puerto
EXPOSE 8000
# Comando para lanzar la app con uvicorn
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


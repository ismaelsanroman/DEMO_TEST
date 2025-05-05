# tests/features/environment.py

import os
import requests

def before_all(context):
    """
    Se ejecuta antes de cualquier escenario:
    - Configura los endpoints de los micros.
    - Obtiene un token válido.
    - Genera environment.properties para Allure.
    """
    # 1. Endpoints
    context.base_urls = {
        "orquestador": "http://localhost:8000",
        "consultas":   "http://localhost:8001",
        "cuentas":     "http://localhost:8002",
        "identidad":   "http://localhost:8003",
        "ia":          "http://localhost:8004",
    }

    # 2. Obtener token
    resp = requests.post(f"{context.base_urls['orquestador']}/token")
    resp.raise_for_status()
    context.token = resp.json().get("access_token")

    # 3. Generar environment.properties para Allure
    results_dir = "reports/behave_results"
    os.makedirs(results_dir, exist_ok=True)
    props = "\n".join(f"{name.upper()}={url}"
                      for name, url in context.base_urls.items())
    with open(os.path.join(results_dir, "environment.properties"), "w") as f:
        f.write(props)

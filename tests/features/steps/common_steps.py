# tests/features/steps/common_steps.py

import json
import requests
from behave import step, step, step, step

# Si prefieres, puedes leer estas URLs de environment.py en lugar de hard-codearlas
MICROS = {
    "orquestador": "http://localhost:8000",
    "consultas": "http://localhost:8001",
    "cuentas": "http://localhost:8002",
    "identidad": "http://localhost:8003",
    "ia": "http://localhost:8004",
}


@step('que tengo un token válido')
def step_impl_token(context):
    """Obtiene el token una sola vez y lo guarda en context.token."""
    resp = requests.post(f"{MICROS['orquestador']}/token")
    resp.raise_for_status()
    context.token = resp.json()['access_token']


@step('la URL del micro "{micro}"')
def step_impl_set_base_url(context, micro):
    """Carga la URL base del micro en context.base_url."""
    context.base_url = MICROS[micro]


@step('envío una petición POST a "{endpoint}" sin payload')
def step_impl_post_no_payload(context, endpoint):
    """POST al endpoint sin cuerpo (para /token)."""
    url = f"{context.base_url}{endpoint}"
    context.response = requests.post(url)


@step('envío una petición POST a "{endpoint}" con pregunta "{pregunta}"')
def step_impl_post_with_pregunta(context, endpoint, pregunta):
    """POST al endpoint con JSON {"pregunta": ...} y Authorization."""
    url = f"{context.base_url}{endpoint}"
    headers = {
        "Authorization": f"Bearer {context.token}",
        "Content-Type": "application/json"
    }
    context.response = requests.post(url, headers=headers, json={"pregunta": pregunta})


@step("el código de respuesta debe ser {status_code:d}")
def step_impl_status_code(context, status_code):
    actual = context.response.status_code
    assert actual == status_code, f"Se esperaba status {status_code}, pero fue {actual}"


@step('la respuesta debe contener "{fragmento}"')
def step_impl_body_contains(context, fragmento):
    """
    Comprueba que el fragmento aparezca, sea en el JSON (cualquier campo/clave)
    o en el texto plano de la respuesta. No distingue mayúsculas.
    """
    fragmento_lower = fragmento.lower()

    try:
        body = context.response.json()
        hay = fragmento_lower in json.dumps(body, ensure_ascii=False).lower()
    except ValueError:
        hay = fragmento_lower in context.response.text.lower()

    assert hay, (
        f"Se esperaba '{fragmento}' en la respuesta.\n"
        f"--> texto/raw: {context.response.text!r}\n"
        f"--> JSON:     {getattr(body, 'keys', lambda: None)()}"
    )

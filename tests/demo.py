# =============================================================================
# scripts/generate_tests.py
# =============================================================================

import os
import ast
import openai
import httpx
from pathlib import Path
from dotenv import load_dotenv

# -------------------------------------------------------
# 🔧 CONFIGURACIÓN
# -------------------------------------------------------
SRC_ROOT     = Path("src")                           # Carpeta raíz donde están los .py a testear
DEST_TESTS   = Path("testspilot_unittests")          # Carpeta destino para los test_<módulo>.py
OPENAI_MODEL = "gpt-4"                               # O "gpt-3.5-turbo" si no tienes acceso a GPT-4
# -------------------------------------------------------


def cargar_api_key_y_config_http_client():
    """
    1) Carga OPENAI_API_KEY desde .env o variables de entorno.
    2) Crea un cliente HTTPX con verify=False y se lo asigna a openai.httpx_client.
    3) Si no encuentra la clave, lanza RuntimeError.
    """
    load_dotenv()  # Lee variables de .env si existe
    clave = os.getenv("OPENAI_API_KEY")
    if not clave:
        raise RuntimeError(
            "🚨 No se encontró la variable OPENAI_API_KEY.\n"
            "   Defínela en .env o expórtala en tu shell."
        )
    openai.api_key = clave

    # 📌 Crear cliente HTTPX desactivando verificación SSL
    cliente_inseguro = httpx.Client(verify=False)
    # Asignamos el cliente a la librería openai para que use ese HTTP client
    openai.httpx_client = cliente_inseguro


def comprobar_api_openai():
    """
    Intenta listar modelos disponibles usando openai.models.list(),
    pero la petición se hace con el httpx.Client(verify=False) configurado,
    de modo que no falle por certificados autofirmados. Si hay cualquier excepción,
    lanza RuntimeError con un mensaje explicativo.
    """
    try:
        # A partir de openai>=1.0.0, la forma correcta de listar modelos es:
        openai.models.list()
    except Exception as e:
        raise RuntimeError(
            "❌ Error al conectar con OpenAI:\n"
            f"   {e}\n\n"
            "   • Verifica que tu clave OPENAI_API_KEY sea correcta.\n"
            "   • Si estás en un entorno corporativo, el SSL puede fallar. Ya "
            "se ha intentado con verify=False, pero revisa tus certificados raíz.\n"
            "   • Asegúrate de tener conexión a Internet.\n"
        )


def extraer_definiciones_py(ruta_archivo: Path) -> dict:
    """
    Extrae definiciones de funciones y clases a nivel superior de un .py usando AST.
    Devuelve un dict con:
      {
        "funciones": [("nombre_función", "código fuente de la función"), ...],
        "clases":    [("NombreClase",    "código fuente de la clase"), ...]
      }
    """
    with ruta_archivo.open("r", encoding="utf-8") as f:
        fuente = f.read()

    tree = ast.parse(fuente)
    defs = {"funciones": [], "clases": []}

    for nodo in tree.body:
        if isinstance(nodo, ast.FunctionDef):
            li = nodo.lineno - 1
            lf = max(n.lineno for n in nodo.body)
            lineas = fuente.splitlines()[li:lf]
            codigo_func = "\n".join(lineas)
            defs["funciones"].append((nodo.name, codigo_func))

        if isinstance(nodo, ast.ClassDef):
            li = nodo.lineno - 1
            lf = nodo.body[-1].lineno
            lineas = fuente.splitlines()[li:lf]
            codigo_cls = "\n".join(lineas)
            defs["clases"].append((nodo.name, codigo_cls))

    return defs


def generar_prompt(nombre_modulo: str, defs: dict) -> str:
    """
    Construye un prompt en español para pedir a GPT-4 que genere tests en pytest
    para las funciones y clases de un módulo dado, cumpliendo con:
      - pytest markers: @pytest.mark.unit, @pytest.mark.<funcionalidad>, @pytest.mark.<tipo>
      - Allure decorators: @allure.feature, @allure.story
      - Logger usage: import logging; logger = logging.getLogger(__name__)
      - Código formateado para Black, Flake8 e Isort
      - Complejidad ciclomática baja (idealmente 1-2 por test)
      - Mutant-testing friendly (tests sencillos con aserciones directas)

    - nombre_modulo: ruta relativa (ej. "input/mcp_adapter_base.py")
    - defs: {"funciones": [("nombre", "código"),], "clases": [("NombreClase", "código"),]}
    """
    prompt = (
        f"### CONTEXTO:\n"
        f"- Módulo Python a testear: '{nombre_modulo}'.\n"
        f"- Queremos generar tests unitarios en pytest que cumplan los siguientes requisitos:\n"
        f"  1. Cada test debe tener:\n"
        f"     • @pytest.mark.unit\n"
        f"     • @pytest.mark.<funcionalidad> indicando la funcionalidad principal (p.ej. agents, network, etc.)\n"
        f"     • @pytest.mark.<tipo> indicando si es 'happy_path', 'exception', 'edge_case', etc.\n"
        f"  2. Cada suite o función de test debe llevar decoradores de Allure para feature y story, p.ej.:\n"
        f"     @allure.feature(\"<Nombre de la funcionalidad>\")\n"
        f"     @allure.story(\"<Historia Concreta o Caso de Uso>\")\n"
        f"  3. Incluir al inicio de cada archivo de test:\n"
        f"     import logging\n"
        f"     logger = logging.getLogger(__name__)\n"
        f"     y dentro de cada test, usar logger.info(\"<mensaje descriptivo>\") para trazabilidad.\n"
        f"  4. El código generado debe pasar **Black**, **Flake8** e **Isort** sin errores:\n"
        f"     • Líneas <= 88 caracteres\n"
        f"     • Importar en tres secciones: Stdlib, bibliotecas de terceros, imports locales.\n"
        f"     • No violar reglas de estilo (espacios, indentación, etc.).\n"
        f"  5. Mantener cada test con complejidad ciclomática baja (1 o 2).\n"
        f"  6. Asegurarse de que los tests sean 'mutation-testing friendly': aserciones simples,\n"
        f"     evitar lógica condicional compleja dentro del test.\n\n"
        f"### DEFINICIONES A TESTEAR:\n"
    )

    # Inserta el código de cada función a testear
    if defs["funciones"]:
        prompt += "## FUNCIONES:\n"
        for fname, fcode in defs["funciones"]:
            prompt += (
                f"\n### Función: {fname}\n"
                f"```python\n"
                f"{fcode}\n"
                f"```\n"
            )

    # Inserta el código de cada clase a testear
    if defs["clases"]:
        prompt += "\n## CLASES:\n"
        for cname, ccode in defs["clases"]:
            prompt += (
                f"\n### Clase: {cname}\n"
                f"```python\n"
                f"{ccode}\n"
                f"```\n"
            )

    prompt += (
        "\n### INSTRUCCIONES ADICIONALES:\n"
        "1) Para cada función o clase, genera tests en pytest que cubran casos:\n"
        "   - Caso nominal (happy path).\n"
        "   - Edge cases relevantes (inputs vacíos, valores límite, excepciones esperadas).\n"
        "2) Cada archivo de test debe tener al inicio:\n"
        "   ```python\n"
        "   import pytest\n"
        "   import logging\n"
        "   import allure\n"
        "   from src.gen_ai_agent_sdk_lib import <subpaquete>  # según la ubicación real\n\n"
        "   logger = logging.getLogger(__name__)\n"
        "   ```\n"
        "3) Cada test debe empezar con algo como:\n"
        "   ```python\n"
        "   @pytest.mark.unit\n"
        "   @pytest.mark.<funcionalidad>  # Ej: @pytest.mark.agents o @pytest.mark.network\n"
        "   @pytest.mark.<tipo>           # Ej: @pytest.mark.happy_path, @pytest.mark.exception, etc.\n"
        "   @allure.feature(\"<Funcionalidad Principal>\")\n"
        "   @allure.story(\"<Caso de Uso o Historia>\")\n"
        "   def test_<nombre_test>(<fixtures_si_es_necesario>):\n"
        "       logger.info(\"<Mensaje descriptivo de inicio de test>\")\n"
        "       # Llamada a la función/clase y aserciones\n"
        "   ```\n"
        "4) Cada test debe tener aserciones claras:\n"
        "   - `assert` simples comparando valores concretos.\n"
        "   - No introducir lógica condicional compleja dentro del test.\n"
        "5) Organizar las importaciones en este orden:\n"
        "   - Módulos estándar de Python\n"
        "   - Bibliotecas de terceros (pytest, allure, requests, etc.)\n"
        "   - Imports locales (`from src.gen_ai_agent_sdk_lib.<subpaquete> import <módulo>`)\n"
        "   Asegúrate de que pasa `isort --profile black`.\n"
        "6) Formatea el archivo final con `black` (líneas <= 88 caracteres, comillas dobles) y\n"
        "   revisa que `flake8` no dé errores.\n"
        "7) Mantén una complejidad ciclomática por test de 1 o 2 (no más de un condicional simple).\n"
        "8) Evita bloques `try/except` dentro de los tests; si esperas excepciones, usa:\n"
        "   ```python\n"
        "   with pytest.raises(<ExcepciónEsperada>):\n"
        "       <llamada que dispara la excepción>\n"
        "   ```\n"
        "9) La estructura de los tests debe quedar en:\n"
        "   `testspilot_unittests/test_<nombre_modulo>.py`\n"
        "10) Devuélvelo TODO en un único bloque de código Python completo, sin explicaciones.\n\n"
        "### EJEMPLO DE MÓDULO A TESTEAR / CASO CONCRETO:\n"
        "- Supongamos que el módulo define una función `send_instruction` que hace una petición HTTP\n"
        "  y decodifica JSON. Queremos tests que cubran respuesta válida y respuesta con JSON inválido.\n\n"
        "#### Ejemplo de función a testear:\n"
        "```python\n"
        "def send_instruction(instruction: str) -> dict:\n"
        "    \"\"\"Envía la instrucción al supervisor y devuelve el JSON parseado\"\"\"\n"
        "    response = requests.post(URL_SUPERVISOR, json={'input': instruction})\n"
        "    data = response.json()\n"
        "    return data\n"
        "```\n\n"
        "#### Ahora genera los tests completos (pytest, allure, logger, marcadores, formato Black/Isort/Flake8, etc.)\n"
    )

    return prompt


def llamada_openai_chat(prompt: str) -> str:
    """
    Llama a la API de OpenAI (v1.x) usando el httpx.Client con verify=False,
    y retorna el texto del primer mensaje (que contendrá los tests en pytest).
    """
    respuesta = openai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Eres un experto en generar tests en pytest para código Python."},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.2,
        max_tokens=2000,
        n=1,
    )
    return respuesta.choices[0].message.content.strip()


def generar_tests_para_modulo(ruta_archivo: Path):
    """
    1) Extrae definiciones de funciones y clases del archivo.
    2) Si no hay definiciones, imprime aviso y retorna.
    3) Genera el prompt y llama a la API de OpenAI.
    4) Crea (o sobrescribe) el fichero test_<módulo>.py en DEST_TESTS.
    """
    nombre_modulo = ruta_archivo.stem
    defs = extraer_definiciones_py(ruta_archivo)

    if not defs["funciones"] and not defs["clases"]:
        print(f"   ⚠️ No hay funciones ni clases a testear en {ruta_archivo.name}. Se salta.")
        return

    prompt = generar_prompt(
        nombre_modulo=str(ruta_archivo.relative_to(SRC_ROOT)),
        defs=defs
    )

    try:
        contenido_tests = llamada_openai_chat(prompt)
    except Exception as e:
        print(f"   ❌ Error al llamar a OpenAI para {ruta_archivo.name}: {e}")
        return

    DEST_TESTS.mkdir(parents=True, exist_ok=True)
    archivo_test = DEST_TESTS / f"test_{nombre_modulo}.py"

    try:
        with archivo_test.open("w", encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write(f"# Test generado automáticamente para {ruta_archivo.name}\n\n")
            f.write(contenido_tests)
            f.write("\n")
        print(f"   ✅ Test creado: {archivo_test.relative_to(Path.cwd())}")
    except Exception as e:
        print(f"   ❌ No se pudo escribir {archivo_test}: {e}")


def generar_tests():
    """
    Flujo principal:
    1) Carga la API Key y configura el httpx.Client con verify=False.
    2) Verifica la conexión a la API de OpenAI (listado de modelos).
    3) Recorre todos los .py en 'src/' (omitendo __init__.py y test_*.py).
    4) Para cada módulo, genera su test en pytest y lo guarda en DEST_TESTS.
    """
    # ------------------------------------------------
    # 1) Carga la clave y configura HTTP client
    # ------------------------------------------------
    try:
        cargar_api_key_y_config_http_client()
        print("🔑 OPENAI_API_KEY detectada correctamente y httpx.Client(verify=False) configurado.")
    except RuntimeError as e:
        print(e)
        return

    # ------------------------------------------------
    # 2) Verifica la conexión con OpenAI
    # ------------------------------------------------
    try:
        print("☑️ Probando conexión con OpenAI (listado de modelos)…")
        comprobar_api_openai()
        print("✅ Conexión con OpenAI OK.\n")
    except RuntimeError as e:
        print(e)
        return

    # ------------------------------------------------
    # 3) Recoge todos los archivos .py válidos
    # ------------------------------------------------
    archivos_fuente = [
        f for f in SRC_ROOT.rglob("*.py")
        if f.name != "__init__.py" and not f.name.startswith("test_")
    ]

    if not archivos_fuente:
        print("⚠️ No se encontraron archivos .py para procesar bajo 'src/'.")
        return

    print(f"🔍 Se van a procesar {len(archivos_fuente)} archivos:\n")
    for f in archivos_fuente:
        print(f"  • {f.relative_to(SRC_ROOT)}")
    print()

    # ------------------------------------------------
    # 4) Genera tests para cada módulo
    # ------------------------------------------------
    for ruta in archivos_fuente:
        print(f"→ Procesando Módulo: {ruta.relative_to(SRC_ROOT)}")
        generar_tests_para_modulo(ruta)
        print()

    print("🎉 Generación de tests completada. Revisa la carpeta:", DEST_TESTS, "\n")


if __name__ == "__main__":
    generar_tests()

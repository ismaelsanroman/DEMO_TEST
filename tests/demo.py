# =============================================================================
# scripts/generate_tests.py
# =============================================================================
import os
import ast
import openai
import requests
from pathlib import Path
from dotenv import load_dotenv

# -------------------------------------------------------
# 🔧 CONFIGURACIÓN (modifica si quieres cambiar rutas o modelo)
# -------------------------------------------------------
SRC_ROOT     = Path("src")                           # Carpeta raíz donde están todos los .py a testear
DEST_TESTS   = Path("testspilot_unittests")          # Carpeta destino para volcar test_<módulo>.py
OPENAI_MODEL = "gpt-4"                               # Puedes usar "gpt-3.5-turbo" si no tienes GPT-4
# -------------------------------------------------------


def cargar_api_key():
    """
    1) Carga OPENAI_API_KEY desde .env (si existe) o desde la variable de entorno.
    2) Si no encuentra la clave, levanta RuntimeError para detener todo.
    """
    load_dotenv()  # lee automáticamente un posible archivo .env
    clave = os.getenv("OPENAI_API_KEY")
    if not clave:
        raise RuntimeError(
            "🚨 No se encontró la variable OPENAI_API_KEY.\n"
            "   Defínela en un fichero .env o expórtala en tu shell."
        )
    openai.api_key = clave


def comprobar_api_openai():
    """
    Hace un “ping” mínimo a la API de OpenAI para verificar que la clave funciona y hay conexión:
    - Llamamos a openai.Model.list() y comprobamos que no falle.
    - Si hay error de autenticación o de conexión, capturamos la excepción y la convertimos en RuntimeError.
    """
    try:
        # Esto devuelve una lista de modelos disponibles; si falla, la excepción salta.
        openai.Model.list()
    except openai.error.AuthenticationError as e:
        raise RuntimeError(f"❌ Clave de OpenAI inválida o caducada: {e}")
    except (openai.error.APIConnectionError, requests.exceptions.RequestException) as e:
        raise RuntimeError(f"❌ No se pudo conectar a OpenAI: {e}")
    except Exception as e:
        raise RuntimeError(f"❌ Error al verificar OpenAI API: {e}")


def extraer_definiciones_py(ruta_archivo: Path) -> dict:
    """
    Dado un archivo Python (ruta_archivo), parsea el AST y devuelve:
      {
        "funciones": [("nombre_función", "código fuente de la función"), ...],
        "clases":    [("NombreClase", "código fuente de la clase"), ...]
      }
    Solo recoge definiciones a nivel superior.
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
    Constrúe un prompt en español para pedir a GPT-4 (o gpt-3.5) que genere
    tests en pytest para todas las funciones y clases del módulo dado.
    - nombre_modulo: ruta relativa del archivo (ej. "input/mcp_adapter_base.py").
    - defs: {"funciones": [...], "clases": [...]}
    """
    prompt = (
        f"Genera tests en pytest para el módulo Python '{nombre_modulo}'.\n"
        "A continuación tienes las definiciones (funciones y/o clases) a testear.\n\n"
    )

    if defs["funciones"]:
        prompt += "## FUNCIONES:\n"
        for (fname, fcode) in defs["funciones"]:
            prompt += f"\n### Función: {fname}\n```python\n{fcode}\n```\n"

    if defs["clases"]:
        prompt += "\n## CLASES:\n"
        for (cname, ccode) in defs["clases"]:
            prompt += f"\n### Clase: {cname}\n```python\n{ccode}\n```\n"

    prompt += (
        "\nInstrucciones:\n"
        "1) Escribe tests en pytest que cubran casos normales y edge-cases.\n"
        "2) Importa el módulo con su ruta completa, por ejemplo:\n"
        "   from src.gen_ai_agent_sdk_lib.subcarpeta import módulo\n"
        "3) Usa nombres descriptivos en las funciones de test (español o inglés).\n"
        "4) Incluye comentarios breves explicando qué prueba cada test.\n\n"
        "Devuélvelo TODO en un único bloque de código Python válido.\n"
    )
    return prompt


def llamada_openai_chat(prompt: str) -> str:
    """
    Llama a la API de OpenAI (v1.x) usando el endpoint de chat completions.
    Retorna únicamente el contenido del mensaje generado por GPT.
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
    1) Extrae funciones y clases de 'ruta_archivo'.
    2) Si no hay definiciones, imprime aviso y retorna.
    3) Construye el prompt y llama a OpenAI.
    4) Crea (o sobrescribe) un fichero test_<módulo>.py en DEST_TESTS.
    """
    nombre_modulo = ruta_archivo.stem  # ej: "mcp_adapter_base"
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
    1) Carga y comprueba la OPENAI_API_KEY.
    2) Verifica que la conexión a OpenAI funcione.
    3) Recorre todos los .py bajo SRC_ROOT (salta __init__.py y test_*.py).
    4) Genera tests para cada módulo y los vuelca en DEST_TESTS.
    """
    # ------------------------------------------------
    # 1) Carga de la clave y chequeo inicial
    # ------------------------------------------------
    try:
        cargar_api_key()
        print("🔑 OPENAI_API_KEY detectada correctamente.")
    except RuntimeError as e:
        print(e)
        return

    try:
        print("☑️ Probando conexión con OpenAI (listado de modelos)…")
        comprobar_api_openai()
        print("✅ Conexión con OpenAI OK.\n")
    except RuntimeError as e:
        print(e)
        return

    # ------------------------------------------------
    # 2) Recuperar lista de archivos .py a procesar
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
    # 3) Generación de tests por cada módulo encontrado
    # ------------------------------------------------
    for ruta in archivos_fuente:
        print(f"→ Procesando Módulo: {ruta.relative_to(SRC_ROOT)}")
        generar_tests_para_modulo(ruta)
        print()

    print("🎉 Generación de tests completada. Revisa la carpeta:", DEST_TESTS, "\n")


if __name__ == "__main__":
    generar_tests()

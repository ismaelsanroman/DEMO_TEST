# -------------------------------------------------------
# scripts/generate_tests.py
# -------------------------------------------------------
import os
import ast
import openai
from pathlib import Path
from dotenv import load_dotenv

# -------------------------------------------------------
# 🔧 CONFIGURACIÓN
# -------------------------------------------------------
SRC_ROOT     = Path("src")                           # Carpeta donde están tus paquetes Python (src/mi_paquete/)
DEST_TESTS   = Path("testspilot_unittests")          # Carpeta destino donde volcará test_<módulo>.py
OPENAI_MODEL = "gpt-4"                               # Modelo a usar (puede ser "gpt-3.5-turbo" si no tienes acceso a GPT-4)
# -------------------------------------------------------


def cargar_api_key():
    """
    Carga la variable OPENAI_API_KEY desde .env (si existe) o desde el entorno.
    Si no la encuentra, lanza RuntimeError con mensaje claro.
    """
    load_dotenv()  # lee automáticamente .env si existe en la raíz
    clave = os.getenv("OPENAI_API_KEY")
    if not clave:
        raise RuntimeError(
            "🚨 No se encontró la variable OPENAI_API_KEY.\n"
            "   Define OPENAI_API_KEY en un archivo .env o expórtala en tu shell."
        )
    openai.api_key = clave


def encontrar_paquete_src() -> Path:
    """
    Busca dentro de SRC_ROOT (src/) la primera carpeta que contenga
    al menos un __init__.py en cualquier subnivel. Eso será tu paquete Python.
    Por ejemplo: src/gen_ai_agent_sdk_lib
    Si no encuentra ninguno, lanza RuntimeError.
    """
    for carpeta in SRC_ROOT.iterdir():
        if not carpeta.is_dir():
            continue
        # Recorre recursivamente para saber si existe un __init__.py
        if any((carpeta / "__init__.py").exists() for _ in carpeta.rglob("__init__.py")):
            return carpeta

    raise RuntimeError(
        "🚨 No se encontró ningún paquete Python en 'src/'.\n"
        "   Asegúrate de tener algo como 'src/mi_paquete/__init__.py'."
    )


def extraer_definiciones_py(ruta_archivo: Path) -> dict:
    """
    Dado un archivo Python (ruta_archivo), parsea el AST y devuelve un dict con:
      {
        "funciones": [("nombre_función", "código fuente completo de la función"), ...],
        "clases":    [("NombreClase", "código fuente completo de la clase"), ...]
      }
    Sólo considera definiciones a nivel superior (no anidadas).
    """
    with ruta_archivo.open("r", encoding="utf-8") as f:
        fuente = f.read()

    tree = ast.parse(fuente)
    defs = {"funciones": [], "clases": []}

    for nodo in tree.body:
        if isinstance(nodo, ast.FunctionDef):
            # Tomamos desde la línea de inicio hasta la última línea de su cuerpo
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
    Construye un prompt en español para pedirle a GPT-4 que genere tests en pytest
    para todas las funciones y clases de ese módulo.
    nombre_modulo = ruta relativa del módulo (por ejemplo: "input/mcp_adapter_base.py")
    defs = {"funciones":[(...)], "clases":[(...)]}
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
        "1) Escribe tests en pytest que cubran casos normales y algunos edge-cases.\n"
        "2) Utiliza la importación completa, por ejemplo:\n"
        "   from src.gen_ai_agent_sdk_lib.subcarpeta import módulo\n"
        "3) Pon nombres descriptivos a cada función de test (en español o inglés).\n"
        "4) Añade comentarios breves explicando qué prueba cada test.\n\n"
        "Devuélvelo TODO en un único bloque de código Python válido.\n"
    )
    return prompt


def llamada_openai_chat(prompt: str) -> str:
    """
    Utiliza la nueva interfaz de openai >= 1.0.0 para crear completions tipo Chat.
    Retorna únicamente el texto que viene en la respuesta (un bloque de código con los tests).
    """
    respuesta = openai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Eres un experto en crear tests en pytest para código Python."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=2000,
        n=1,
    )
    # La respuesta final como string
    return respuesta.choices[0].message.content.strip()


def generar_tests_para_modulo(ruta_archivo: Path, carpeta_paquete: Path):
    """
    1) Extrae funciones/clases del módulo (ruta_archivo).
    2) Si hay definiciones, construye un prompt y llama a la API de OpenAI.
    3) Crea (o sobrescribe) un fichero test_<módulo>.py dentro de DEST_TESTS.
    """
    nombre_modulo = ruta_archivo.stem  # ej.: "mcp_adapter_base"
    defs = extraer_definiciones_py(ruta_archivo)

    if not defs["funciones"] and not defs["clases"]:
        print(f"   ⚠️ No hay funciones o clases a testear en {ruta_archivo.name}. Se salta.")
        return

    prompt = generar_prompt(
        nombre_modulo=str(ruta_archivo.relative_to(carpeta_paquete)),
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
    1) Carga la API Key de OpenAI.
    2) Detecta automáticamente el paquete Python en src/.
    3) Recorre todos los .py (sin __init__.py ni test_*.py) dentro de ese paquete.
    4) Para cada módulo, invoca a OpenAI y genera un fichero test_<módulo>.py en DEST_TESTS.
    """
    try:
        cargar_api_key()
    except RuntimeError as e:
        print(e)
        return

    print("🧪 Iniciando generación de tests mediante OpenAI (v1.x)…\n")

    try:
        carpeta_paquete = encontrar_paquete_src()
    except RuntimeError as e:
        print(e)
        return

    print(f"📦 Paquete detectado en: {carpeta_paquete}\n")

    archivos_fuente = [
        f for f in carpeta_paquete.rglob("*.py")
        if f.name != "__init__.py" and not f.name.startswith("test_")
    ]

    if not archivos_fuente:
        print("⚠️ No se encontraron archivos .py para generar tests.")
        return

    print(f"🔍 Se van a procesar {len(archivos_fuente)} archivos:\n")
    for f in archivos_fuente:
        print(f"  • {f.relative_to(carpeta_paquete)}")
    print()

    for ruta in archivos_fuente:
        print(f"→ Procesando Módulo: {ruta.relative_to(carpeta_paquete)}")
        generar_tests_para_modulo(ruta, carpeta_paquete)
        print()

    print("🎉 Generación de tests completada. Revisa la carpeta:", DEST_TESTS, "\n")


if __name__ == "__main__":
    generar_tests()

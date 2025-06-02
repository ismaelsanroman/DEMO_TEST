# ------------------------------------------
# scripts/generate_tests.py
# ------------------------------------------
import os
import ast
import openai
from pathlib import Path
from dotenv import load_dotenv

# ------------------------------------------
# 🔧 CONFIGURACIÓN
# ------------------------------------------
SRC_ROOT    = Path("src")                           # Carpeta donde buscar el paquete Python
DEST_TESTS  = Path("testspilot_unittests")          # Carpeta donde volcar los test_*.py
OPENAI_MODEL = "gpt-4"                              # Modelo que usarás (puede ser gpt-3.5-turbo si no tienes GPT-4)
# ------------------------------------------

def cargar_api_key():
    """
    Carga la variable OPENAI_API_KEY desde .env (si existe),
    o bien asume que ya está en el entorno.
    """
    load_dotenv()  # lee automáticamente .env si existe
    clave = os.getenv("OPENAI_API_KEY")
    if not clave:
        raise RuntimeError(
            "🚨 No se encontró la variable OPENAI_API_KEY. "
            "Asegúrate de definirla en un .env o exportarla en tu shell."
        )
    openai.api_key = clave


def encontrar_paquete_src() -> Path:
    """
    Busca en /src la carpeta que contenga un __init__.py en algún subnivel.
    Devuelve la primera carpeta que cumpla. Si no encuentra ninguna, lanza excepción.
    Por ejemplo: src/gen_ai_agent_sdk_lib
    """
    for carpeta in SRC_ROOT.iterdir():
        if not carpeta.is_dir():
            continue
        # Si dentro de esta carpeta (o sus subcarpetas) hay al menos un __init__.py:
        if any((carpeta / "__init__.py").exists() for _ in carpeta.rglob("__init__.py")):
            return carpeta
    raise RuntimeError(
        "🚨 No se encontró ningún paquete Python dentro de 'src/'.\n"
        "   Debes tener algo así como 'src/mi_paquete/__init__.py'."
    )


def extraer_definiciones_py(ruta_archivo: Path) -> dict:
    """
    Abre el archivo Python, parsea el AST y devuelve un diccionario:
      {
        "funciones": [("nombre_funcion", "código fuente de la función"), ...],
        "clases":    [("NombreClase", "código fuente de la clase"), ...]
      }
    Solo considera definiciones a nivel superior.
    """
    with ruta_archivo.open("r", encoding="utf-8") as f:
        fuente = f.read()

    # Parseamos el AST
    tree = ast.parse(fuente)

    defs = {"funciones": [], "clases": []}

    # Recorremos todos los nodos a nivel superior
    for nodo in tree.body:
        # Si es def foo(...)
        if isinstance(nodo, ast.FunctionDef):
            # Obtenemos el código original de la función (incluyendo docstrings)
            lineno_inicio = nodo.lineno - 1
            # Para obtener el final, tomamos el lineno del último nodo en el cuerpo de la función
            lineno_fin = max(n.lineno for n in nodo.body)  # línea del ultimo statement
            lineas = fuente.splitlines()[lineno_inicio:lineno_fin]
            codigo_func = "\n".join(lineas)
            defs["funciones"].append((nodo.name, codigo_func))

        # Si es class Foo(...)
        if isinstance(nodo, ast.ClassDef):
            lineno_inicio = nodo.lineno - 1
            lineno_fin = nodo.body[-1].lineno  # línea del último statement en la clase
            lineas = fuente.splitlines()[lineno_inicio:lineno_fin]
            codigo_cls = "\n".join(lineas)
            defs["clases"].append((nodo.name, codigo_cls))

    return defs


def generar_prompt(nombre_modulo: str, defs: dict) -> str:
    """
    Genera un prompt en español que le pediremos a GPT-4 para crear tests en pytest
    para las funciones y clases encontradas en el módulo.
    """
    prompt = f"Genera un o varios tests en pytest para el módulo Python: '{nombre_modulo}'.\n"
    prompt += "A continuación tienes las definiciones a testear.\n\n"

    if defs["funciones"]:
        prompt += "## FUNCIONES:\n"
        for (fname, fcode) in defs["funciones"]:
            prompt += f'\n### Función: {fname}\n```python\n{fcode}\n```\n'

    if defs["clases"]:
        prompt += "\n## CLASES:\n"
        for (cname, ccode) in defs["clases"]:
            prompt += f'\n### Clase: {cname}\n```python\n{ccode}\n```\n'

    prompt += (
        "\nInstrucciones:\n"
        "1. Escribe tests en pytest que cubran casos normales y algunos edge cases.\n"
        "2. Importa el módulo con su ruta completa (por ejemplo: from src.gen_ai_agent_sdk_lib.<subcarpeta> import <módulo>)\n"
        "3. Cada test debe corregirse si falta importar algo.\n"
        "4. Pon nombres descriptivos a cada función de test (en castellano o inglés).\n"
        "5. Incluye comentarios breves indicando lo que pruebas.\n"
        "\nDevuélvelo TODO en un bloque de código Python válido.\n"
    )
    return prompt


def llamada_openai_chat(prompt: str) -> str:
    """
    Llama a la API de OpenAI usando el modelo definido en OPENAI_MODEL.
    Retorna el código generado como texto (string).
    """
    respuesta = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Eres un experto en crear tests con pytest para código Python."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=2000,
        n=1,
    )
    return respuesta.choices[0].message.content.strip()


def generar_tests_para_modulo(ruta_archivo: Path, carpeta_paquete: Path):
    """
    1) Extrae funciones y clases del módulo (ruta_archivo)
    2) Genera prompt y llama a OpenAI para crear los tests.
    3) Crea/reescribe un archivo test_<módulo>.py en DEST_TESTS.
    """
    nombre_modulo = ruta_archivo.stem  # por ejemplo: "mcp_adapter_base"
    defs = extraer_definiciones_py(ruta_archivo)

    if not defs["funciones"] and not defs["clases"]:
        # No hay nada que testear en este módulo
        print(f"   ⚠️ No hay funciones o clases a testear en {ruta_archivo.name}, se salta.")
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

    # Construimos ruta de destino: test_<módulo>.py
    archivo_test = DEST_TESTS / f"test_{nombre_modulo}.py"

    try:
        # Sobre escribimos si ya existe
        DEST_TESTS.mkdir(parents=True, exist_ok=True)
        with archivo_test.open("w", encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write(f"# Test generado automáticamente para {ruta_archivo.name}\n\n")
            f.write(contenido_tests)
            f.write("\n")
        print(f"   ✅ Test creado: {archivo_test.relative_to(Path.cwd())}")
    except Exception as e:
        print(f"   ❌ No se pudo escribir el fichero {archivo_test}: {e}")


def generar_tests():
    """
    1) Carga la API Key de OpenAI
    2) Encuentra el paquete Python en src/
    3) Recorre recursivamente todos los .py (omitimos __init__.py y test_*.py)
    4) Para cada módulo, invoca a OpenAI para generar tests y los salva en DEST_TESTS/
    """
    try:
        cargar_api_key()
    except RuntimeError as e:
        print(e)
        return

    print("🧪 Iniciando generación de tests mediante OpenAI…")

    # 2) Detectar paquete
    try:
        carpeta_paquete = encontrar_paquete_src()
    except RuntimeError as e:
        print(e)
        return

    print(f"📦 Paquete detectado en: {carpeta_paquete}\n")

    # 3) Listar todos los archivos .py a testear
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

    # 4) Por cada módulo, generamos test mediante la llamada a OpenAI
    for ruta in archivos_fuente:
        print(f"→ Procesando Módulo: {ruta.relative_to(carpeta_paquete)}")
        generar_tests_para_modulo(ruta, carpeta_paquete)
        print()  # línea en blanco entre módulos

    print("🎉 Generación de tests completada. Revisa la carpeta:", DEST_TESTS, "\n")


if __name__ == "__main__":
    generar_tests()

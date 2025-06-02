import subprocess
import shutil
from pathlib import Path

# ----------------------------------------------------------------------------------------------------------------------
# 🔧 CONFIGURACIÓN
# ----------------------------------------------------------------------------------------------------------------------
SRC_ROOT    = Path("src")                                # Carpeta raíz donde están todos los paquetes (src/mi_paquete/)
TESTS_DIR   = Path("testspilot_unittests")               # Carpeta de destino para los tests generados
TESTPILOT   = ["pipenv", "run", "testpilot"]             # Comando base para llamar a TestPilot
# ----------------------------------------------------------------------------------------------------------------------


def encontrar_paquete_src() -> Path:
    """
    Busca dentro de /src la carpeta que contenga al menos un '__init__.py'.
    Devuelve la primera carpeta que cumpla; si no hay ninguna, lanza excepción.
    """
    for carpeta in SRC_ROOT.iterdir():
        if not carpeta.is_dir():
            continue
        # Si dentro de esta carpeta (o sus subdirectorios) hay un __init__.py, la tomamos como paquete
        if any((carpeta / "__init__.py").exists() for _ in carpeta.rglob("__init__.py")):
            return carpeta
    raise RuntimeError(
        "❌ No se encontró ningún paquete Python dentro de 'src/'.\n"
        "   Asegúrate de tener algo como 'src/mi_paquete/__init__.py'."
    )


def generar_tests():
    """
    1) Detecta el paquete Python en /src
    2) Ejecuta TestPilot pasándole la carpeta entera con '-d <directorio>'
    3) Una vez que TestPilot haya generado sus 'test_*.py' junto a cada módulo, los mueve
       todos a TESTS_DIR, respetando únicamente el nombre del fichero (sin jerarquía).
    """
    print("🧪 Iniciando generación de tests con TestPilot...")

    # 1. Buscar la carpeta del paquete (p. ej. src/gen_ai_agent_sdk_lib)
    try:
        paquete = encontrar_paquete_src()
    except RuntimeError as e:
        print(e)
        return

    print(f"📦 Paquete detectado: {paquete}")

    # 2. Asegurar que existe TESTS_DIR
    TESTS_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Llamar a TestPilot con la opción '-d <directorio_paquete>'
    #    Esto generará, junto a cada .py del paquete, un 'test_<módulo>.py'.
    cmd = TESTPILOT + ["-d", str(paquete)]
    print(f"🚀 Ejecutando: {' '.join(cmd)}")
    resultado = subprocess.run(cmd, capture_output=True, text=True)

    if resultado.returncode != 0:
        print("❌ Falló TestPilot al generar tests para todo el paquete:")
        print(resultado.stderr.strip())
        return
    else:
        print("✅ TestPilot completó la generación de tests para todos los módulos.")

    # 4. Buscar todos los 'test_*.py' generados bajo el paquete y moverlos a TESTS_DIR
    tests_generados = list(paquete.rglob("test_*.py"))
    if not tests_generados:
        print("⚠️ No se encontraron archivos 'test_*.py' generados dentro de la carpeta del paquete.")
        return

    for ruta_test in tests_generados:
        nombre_test = ruta_test.name
        destino = TESTS_DIR / nombre_test

        # Si ya existía un test con ese nombre en TESTS_DIR, lo borramos para sobreescribir
        if destino.exists():
            destino.unlink()

        try:
            shutil.move(str(ruta_test), str(destino))
            print(f"   ✅ Movido: {ruta_test.relative_to(Path.cwd())} → {destino.relative_to(Path.cwd())}")
        except Exception as e:
            # Si falla el movimiento, dejamos el test en la ubicación original y avisamos
            print(f"   ❌ No se pudo mover '{nombre_test}' a '{TESTS_DIR}': {e}")

    print("\n🎉 Generación y reubicación de tests finalizada.")


if __name__ == "__main__":
    generar_tests()

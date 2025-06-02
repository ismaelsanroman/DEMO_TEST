import subprocess
import shutil
from pathlib import Path

# ------------------------------------------------------------
# 🔧 CONFIGURACIÓN
# ------------------------------------------------------------
SRC_ROOT  = Path("src")                              # Raíz donde están todos los paquetes Python
TESTS_DIR = Path("testspilot_unittests")             # Carpeta destino para alojar TODOS los test_*.py
# ------------------------------------------------------------

def encontrar_paquete_src() -> Path:
    """
    Busca en /src la carpeta que contenga al menos un '__init__.py'
    en algún subdirectorio. Retorna la primera que cumpla.
    Si no hay ninguna, lanza RuntimeError.
    """
    for carpeta in SRC_ROOT.iterdir():
        if not carpeta.is_dir():
            continue

        # Si en esta carpeta (o en cualquiera de sus subcarpetas) hay un __init__.py,
        # la tomamos como 'mi_paquete'.
        if any((carpeta / "__init__.py").exists() for _ in carpeta.rglob("__init__.py")):
            return carpeta

    raise RuntimeError(
        "❌ No se encontró ningún paquete Python dentro de 'src/'.\n"
        "   Debes tener algo como 'src/mi_paquete/__init__.py'."
    )


def generar_tests():
    """
    1) Detecta el paquete bajo src/
    2) Invoca   pipenv run python -m testpilot   SIN argumentos   para que TestPilot
       genere un 'test_<módulo>.py' junto a cada .py de ese paquete.
    3) Recorre todos los archivos test_*.py recién creados y los mueve a TESTS_DIR.
    """
    print("🧪 Iniciando generación de tests con TestPilot…")

    # 1) Detectar el paquete principal dentro de src/
    try:
        paquete = encontrar_paquete_src()
    except RuntimeError as e:
        print(e)
        return

    print(f"📦 Paquete detectado: {paquete}")

    # 2) Crear carpeta destino (si no existe)
    TESTS_DIR.mkdir(parents=True, exist_ok=True)

    # 3) Ejecutar TestPilot sin argumentos posicionales
    #    (TestPilot busca automáticamente los .py dentro del paquete y genera los test_*.py)
    cmd = ["pipenv", "run", "python", "-m", "testpilot"]
    print(f"🚀 Ejecutando: {' '.join(cmd)}")
    resultado = subprocess.run(cmd, capture_output=True, text=True)

    if resultado.returncode != 0:
        print("❌ Falló TestPilot al generar tests para TODO el paquete:")
        print(resultado.stderr.strip())
        return
    else:
        print("✅ TestPilot completó la generación de tests para todos los módulos.")

    # 4) Ahora, TestPilot habrá creado en cada subcarpeta de `paquete` un archivo test_<módulo>.py.
    #    Buscamos recursivamente todos estos test_*.py y los movemos a TESTS_DIR.
    tests_generados = list(paquete.rglob("test_*.py"))
    if not tests_generados:
        print("⚠️ No se encontró ningún 'test_*.py' generado dentro de la carpeta del paquete.")
        return

    for ruta_test in tests_generados:
        nombre_test = ruta_test.name
        destino = TESTS_DIR / nombre_test

        # Si ya hay un test con el mismo nombre en TESTS_DIR, lo borramos para sobreescribir
        if destino.exists():
            destino.unlink()

        try:
            shutil.move(str(ruta_test), str(destino))
            print(f"   ✅ Movido: {ruta_test.relative_to(Path.cwd())} → {destino.relative_to(Path.cwd())}")
        except Exception as e:
            print(f"   ❌ No se pudo mover '{nombre_test}' a '{TESTS_DIR}': {e}")
            # En caso de error, dejamos el test en la ubicación original

    print("\n🎉 Generación y reubicación de tests finalizada.")


if __name__ == "__main__":
    generar_tests()

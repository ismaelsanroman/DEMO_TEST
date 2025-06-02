import subprocess
import shutil
from pathlib import Path

# ----------------------------------------------------------------------------------------------------------------------
# 🔧 CONFIGURACIÓN (Si quisieras cambiar la carpeta de destino, basta con modificar TESTS_DIR)
# ----------------------------------------------------------------------------------------------------------------------
SRC_ROOT    = Path("src")                               # Carpeta raíz de código fuente
TESTS_DIR   = Path("testspilot_unittests")              # Carpeta donde irán todos los tests generados
TESTPILOT   = ["pipenv", "run", "testpilot"]            # Comando base para llamar a TestPilot
# ----------------------------------------------------------------------------------------------------------------------


def encontrar_paquete_src() -> Path:
    """
    Busca dentro de /src la carpeta que contenga un __init__.py (asumiendo convención 'src/mi_paquete/').
    Devuelve la primera carpeta que cumpla; si no encuentra, lanza excepción.
    """
    for carpeta in SRC_ROOT.iterdir():
        if not carpeta.is_dir():
            continue
        # Si dentro de esta carpeta existe al menos un __init__.py en cualquier subnivel:
        if any((carpeta / "__init__.py").exists() for _ in carpeta.rglob("__init__.py")):
            return carpeta
    raise RuntimeError("❌ No se encontró ningún paquete Python dentro de 'src/'. "
                       "Asegúrate de tener algo como 'src/mi_paquete/__init__.py'.")


def generar_tests():
    """
    Recorre recursivamente todos los archivos .py bajo el paquete detectado, 
    genera su test con TestPilot y mueve cada test a TESTS_DIR.
    """
    print("🧪 Iniciando generación de tests con TestPilot...")

    # 1. Buscar carpeta de paquete dentro de src
    try:
        paquete = encontrar_paquete_src()
    except RuntimeError as e:
        print(e)
        return

    print(f"📦 Paquete detectado: {paquete}")

    # 2. Asegurar que exista la carpeta destino para los tests
    TESTS_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Listar todos los archivos .py válidos (omitimos __init__.py y test_*.py)
    archivos_fuente = [
        archivo for archivo in paquete.rglob("*.py")
        if not archivo.name.startswith("test_")
        and archivo.name != "__init__.py"
    ]

    if not archivos_fuente:
        print("⚠️ No se encontraron archivos .py para generar tests.")
        return

    # 4. Para cada archivo, invocar TestPilot y luego mover el test generado
    for archivo in archivos_fuente:
        rel_path = archivo.relative_to(paquete)
        print(f"\n🔍 Procesando: {rel_path}")

        # 4.1. Ejecutar TestPilot: éste creará 'test_<archivo.stem>.py' al lado del archivo original
        cmd = TESTPILOT + [str(archivo)]
        resultado = subprocess.run(cmd, capture_output=True, text=True)

        if resultado.returncode != 0:
            print(f"❌ Error al generar test para {archivo.name}:")
            print(resultado.stderr.strip())
            continue

        # 4.2. Construir el nombre esperado del test generado
        nombre_test = f"test_{archivo.stem}.py"
        ruta_test_original = archivo.parent / nombre_test

        # 4.3. Verificar que efectivamente se haya generado ese test
        if not ruta_test_original.exists():
            print(f"⚠️ Test esperado no encontrado: {ruta_test_original}")
            continue

        # 4.4. Mover el test generado a la carpeta TESTS_DIR
        destino = TESTS_DIR / nombre_test

        try:
            # Si ya existe un test con el mismo nombre, lo sobreescribimos
            if destino.exists():
                destino.unlink()

            shutil.move(str(ruta_test_original), str(destino))
            print(f"✅ Test movido a: {destino.relative_to(Path.cwd())}")

        except Exception as e:
            print(f"❌ No se pudo mover {nombre_test} a {TESTS_DIR}: {e}")
            # (en caso de fallo, dejamos el test en su ubicación original)

    print("\n🎉 Generación de tests finalizada.")


if __name__ == "__main__":
    generar_tests()

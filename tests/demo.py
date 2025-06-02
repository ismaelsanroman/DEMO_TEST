import subprocess
import shutil
from pathlib import Path

# ----------------------------------------------------------------------------------------------------------------------
# 🔧 CONFIGURACIÓN
# ----------------------------------------------------------------------------------------------------------------------
SRC_ROOT  = Path("src")                              # Carpeta raíz donde están todos los paquetes (src/mi_paquete/)
TESTS_DIR = Path("testspilot_unittests")             # Carpeta de destino para los tests generados
# ----------------------------------------------------------------------------------------------------------------------


def encontrar_paquete_src() -> Path:
    """
    Busca en /src la carpeta que tenga al menos un '__init__.py' en cualquier subdirectorio.
    Devuelve la primera que cumpla esa condición, o lanza RuntimeError si no hay ninguna.
    """
    for carpeta in SRC_ROOT.iterdir():
        if not carpeta.is_dir():
            continue
        # Si en esta carpeta (o en cualquiera de sus subcarpetas) existe un __init__.py, la tomamos como paquete
        if any((carpeta / "__init__.py").exists() for _ in carpeta.rglob("__init__.py")):
            return carpeta

    raise RuntimeError(
        "❌ No se encontró ningún paquete Python dentro de 'src/'.\n"
        "   Asegúrate de tener algo como 'src/mi_paquete/__init__.py'."
    )


def generar_tests():
    """
    1) Detecta el paquete Python en /src
    2) Para cada .py dentro de ese paquete (excepto __init__.py y test_*.py), invoca:
         pipenv run python -m testpilot <archivo>
       que genera junto al archivo un test llamado test_<archivo>.py
    3) Entonces busca todos los test_*.py recién creados y los mueve a TESTS_DIR,
       dejando así limpio el árbol de src/ y concentrando todos los tests en testspilot_unittests/.
    """
    print("🧪 Iniciando generación de tests con TestPilot (módulo Python)...")

    # 1) Buscar el paquete dentro de src/
    try:
        paquete = encontrar_paquete_src()
    except RuntimeError as e:
        print(e)
        return

    print(f"📦 Paquete detectado: {paquete}")

    # 2) Crear carpeta destino (si no existe)
    TESTS_DIR.mkdir(parents=True, exist_ok=True)

    # 3) Listar todos los .py válidos (omitimos __init__.py y test_*.py)
    archivos_fuente = [
        archivo for archivo in paquete.rglob("*.py")
        if not archivo.name.startswith("test_")
        and archivo.name != "__init__.py"
    ]

    if not archivos_fuente:
        print("⚠️ No se encontraron archivos .py para generar tests.")
        return

    # 4) Para cada archivo, invocar TestPilot como módulo de Python:
    for archivo in archivos_fuente:
        rel_path = archivo.relative_to(paquete)
        print(f"\n🔍 Procesando: {rel_path}")

        # Comando: pipenv run python -m testpilot <ruta_del_archivo>
        cmd = ["pipenv", "run", "python", "-m", "testpilot", str(archivo)]
        resultado = subprocess.run(cmd, capture_output=True, text=True)

        if resultado.returncode != 0:
            print(f"❌ Error al generar test para {archivo.name}:")
            print(resultado.stderr.strip())
            continue
        else:
            print(f"✅ TestPilot ejecutado OK para {archivo.name}")

        # 5) El test generado se llama test_<archivo.stem>.py y está junto al archivo fuente
        nombre_test = f"test_{archivo.stem}.py"
        ruta_test_original = archivo.parent / nombre_test

        if not ruta_test_original.exists():
            print(f"⚠️ No se encontró el test generado esperado: {ruta_test_original}")
            continue

        # 6) Mover test_<archivo> a TESTS_DIR
        destino = TESTS_DIR / nombre_test

        try:
            if destino.exists():
                destino.unlink()   # Si ya había uno con el mismo nombre, lo borramos (sobreescribimos)
            shutil.move(str(ruta_test_original), str(destino))
            print(f"   📂 Movido: {ruta_test_original.relative_to(Path.cwd())}  →  {destino.relative_to(Path.cwd())}")
        except Exception as e:
            print(f"❌ Error moviendo {nombre_test} a {TESTS_DIR}: {e}")
            # Si falla moverlo, dejamos el test en su ubicación original y pasamos al siguiente

    print("\n🎉 Generación y reubicación de tests finalizada.")


if __name__ == "__main__":
    generar_tests()

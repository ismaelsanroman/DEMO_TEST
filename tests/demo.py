#!/usr/bin/env python3
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONFIG = os.path.join(ROOT, 'config.toml')
DB = os.path.join(ROOT, 'cr_session.sqlite')
# PARSER = os.path.join(HERE, 'parse_mutation_report.py')

def run(cmd, **kwargs):
    print(f"🛠 Ejecutando --> {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)
        print(result.stdout)
        if result.stderr:
            print(f"[stderr] {result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar: {' '.join(cmd)}")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)

def main():
    print(f"📁 Ruta esperada de la BD: {DB}")

    # 1. Realiza el Init de cosmic-ray si no existe la base de datos
    if not os.path.exists(DB):
        print("🧪 No se encontró la base de datos. Generando con 'cosmic-ray init'...")
        run([sys.executable, '-m', 'cosmic_ray.cli', 'init', CONFIG, DB, '--force'])

        if not os.path.exists(DB):
            print(f"❌ Error: No se pudo crear la base de datos en {DB}.")
            sys.exit(1)
    else:
        print(f"✅ {DB} ya existe, saltando init.")

    # 2. Ejecuta los mutantes
    run([sys.executable, '-m', 'cosmic_ray.cli', 'exec', CONFIG, DB])

    # 3. Vuelca toda la sesión a un JSON
    full_report = os.path.join(ROOT, 'full_report.json')
    with open(full_report, 'w') as out:
        run([sys.executable, '-m', 'cosmic_ray.cli', 'dump', DB], stdout=out)
    print(f"🟢 Reporte completo guardado en: {full_report}")

    # 4. TODO: Solucionar el parseo del JSON
    # run([sys.executable, PARSER, full_report])

    return 0

if __name__ == '__main__':
    sys.exit(main())

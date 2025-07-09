#!/usr/bin/env python3
"""
mutation_check.py

Este script orquesta las pruebas de mutación usando Cosmic Ray.
Realiza los siguientes pasos:
1. Inicializa la base de datos de Cosmic Ray si aún no existe.
2. Ejecuta la sesión de testing de mutaciones.
3. Genera un informe de mutación usando `cr-report` y lo guarda en un fichero de texto.
"""

import sys
import logging
import subprocess
import argparse
from pathlib import Path

# Default configuration constants
DEFAULT_CONFIG   = Path(__file__).parent.parent / "config.toml"
DEFAULT_DB       = Path(__file__).parent.parent / "cr_session.sqlite"
DEFAULT_LOG_DIR  = Path(__file__).parent.parent / "logs"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )


def run_command(cmd: list) -> None:
    """
    Ejecuta un comando externo y registra su salida.
    """
    logging.info("Running command: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        logging.info(result.stdout.strip())
    if result.returncode != 0:
        logging.error("Command failed (exit %d): %s", result.returncode, result.stderr.strip())
        sys.exit(result.returncode)


def initialize_database(config: Path, db: Path) -> None:
    if not db.exists():
        logging.info("Database not found, initializing: %s", db)
        run_command(["cosmic-ray", "init", str(config), str(db), "--force"])
    else:
        logging.info("Database already exists, skipping initialization.")


def execute_mutations(config: Path, db: Path) -> None:
    run_command(["cosmic-ray", "exec", str(config), str(db)])


def generate_text_report(db: Path, out_path: Path) -> int:
    """
    Genera un informe de texto usando `cr-report` y lo guarda en out_path.
    Devuelve el código de salida del comando.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    logging.info("Generating mutation report: %s", out_path)
    with out_path.open("w", encoding="utf-8") as f:
        result = subprocess.run(
            ["pipenv", "run", "cr-report", str(db)],
            stdout=f,
            stderr=subprocess.PIPE,
            text=True
        )
    if result.returncode != 0:
        logging.error("Failed to generate report: %s", result.stderr.strip())
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute Cosmic Ray mutation tests and generate text report via cr-report"
    )
    parser.add_argument(
        "--config", "-c", type=Path, default=DEFAULT_CONFIG,
        help="Path to the Cosmic Ray config.toml"
    )
    parser.add_argument(
        "--db", "-d", type=Path, default=DEFAULT_DB,
        help="Path to the Cosmic Ray SQLite database"
    )
    parser.add_argument(
        "--log-dir", "-l", type=Path, default=DEFAULT_LOG_DIR,
        help="Directory donde se guardará el informe de texto"
    )
    args = parser.parse_args()

    setup_logging()
    initialize_database(args.config, args.db)
    execute_mutations(args.config, args.db)

    report_file = args.log_dir / "cosmic_report.txt"
    exit_code = generate_text_report(args.db, report_file)
    if exit_code != 0:
        return exit_code

    logging.info("Mutation report generated successfully at %s", report_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())

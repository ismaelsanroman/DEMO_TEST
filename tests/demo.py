#!/usr/bin/env python3
"""
mutation_check.py

Este script orquesta las pruebas de mutación usando Cosmic Ray.
Realiza los siguientes pasos:
1. Inicializa la base de datos de Cosmic Ray si aún no existe.
2. Ejecuta la sesión de testing de mutaciones.
3. Genera un informe de texto con `cr-report`.
4. Parsea el informe para extraer métricas y líneas de mutantes supervivientes.
5. Genera un MD con los mutantes supervivientes (si existen).
6. Verifica que la cobertura mínima (100 - supervivencia %) alcance el umbral.
"""

import sys
import logging
import subprocess
import argparse
import re
from pathlib import Path
from typing import List, Tuple

# Default configuration constants
DEFAULT_CONFIG   = Path(__file__).parent.parent / "config.toml"
DEFAULT_DB       = Path(__file__).parent.parent / "cr_session.sqlite"
DEFAULT_LOG_DIR  = Path(__file__).parent.parent / "logs"
DEFAULT_MIN_SCORE = 80.0


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )


def run_command(cmd: List[str]) -> subprocess.CompletedProcess:
    logging.info("Running command: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True)


def initialize_database(config: Path, db: Path) -> None:
    if not db.exists():
        logging.info("Database not found, initializing: %s", db)
        result = run_command(["cosmic-ray", "init", str(config), str(db), "--force"])
        if result.returncode != 0:
            logging.error("Initialization failed: %s", result.stderr.strip())
            sys.exit(result.returncode)
    else:
        logging.info("Database already exists, skipping initialization.")


def execute_mutations(config: Path, db: Path) -> None:
    result = run_command(["cosmic-ray", "exec", str(config), str(db)])
    if result.returncode != 0:
        logging.error("Mutation execution failed: %s", result.stderr.strip())
        sys.exit(result.returncode)


def generate_text_report(db: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    logging.info("Generating mutation report: %s", out_path)
    result = subprocess.run(
        ["pipenv", "run", "cr-report", str(db)],
        stdout=out_path.open("w", encoding="utf-8"),
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        logging.error("Failed to generate report: %s", result.stderr.strip())
        sys.exit(result.returncode)


def parse_text_report(report_path: Path) -> Tuple[int, float, int, float, List[str]]:
    """
    Lee el informe de texto y extrae:
    - total_jobs
    - supervivencia_pct (porcentaje de mutantes sobrevivientes)
    - surviving_count
    - surviving_pct
    - survivors_lines (líneas completas de mutantes no matados)
    """
    total_jobs = 0
    surviving_count = 0
    surviving_pct = 0.0
    survivors_lines: List[str] = []
    # patrones de resumen
    re_total = re.compile(r"^\s*total jobs:\s*(\d+)", re.IGNORECASE)
    re_surv = re.compile(r"^\s*surviving mutants:\s*(\d+)\s*\((?P<pct>[0-9.]+)%\)", re.IGNORECASE)
    # patrón de línea de mutante
    re_job = re.compile(r"^\[job-id\].*test outcome:\s*(TestOutcome\.(?P<outcome>\w+))")

    for line in report_path.read_text(encoding="utf-8").splitlines():
        m_total = re_total.match(line)
        if m_total:
            total_jobs = int(m_total.group(1))
            continue
        m_surv = re_surv.match(line)
        if m_surv:
            surviving_count = int(m_surv.group(1))
            surviving_pct = float(m_surv.group('pct'))
            continue
        # capturar líneas de mutantes supervivientes
        m_job = re_job.match(line)
        if m_job and m_job.group('outcome') != 'KILLED':
            survivors_lines.append(line.strip())

    return total_jobs, surviving_pct, surviving_count, 100.0 - surviving_pct, survivors_lines


def write_survivors_md(survivors: List[str], log_dir: Path) -> Path:
    md_path = log_dir / "survivors.md"
    if not survivors:
        return md_path
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.info("Writing survivors markdown: %s", md_path)
    lines = ["# Mutantes Supervivientes", ""]
    for s in survivors:
        lines.append(f"- `{s}`")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute Cosmic Ray mutation tests and validate coverage via cr-report"
    )
    parser.add_argument("--config", "-c", type=Path, default=DEFAULT_CONFIG,
                        help="Path to the Cosmic Ray config.toml")
    parser.add_argument("--db", "-d", type=Path, default=DEFAULT_DB,
                        help="Path to the Cosmic Ray SQLite database")
    parser.add_argument("--log-dir", "-l", type=Path, default=DEFAULT_LOG_DIR,
                        help="Directory donde se guardarán los informes")
    parser.add_argument("--min-score", "-m", type=float, default=DEFAULT_MIN_SCORE,
                        help="Cobertura mínima (%) requerida, ej.: 80.0")
    args = parser.parse_args()

    setup_logging()
    initialize_database(args.config, args.db)
    execute_mutations(args.config, args.db)

    report_txt = args.log_dir / "cosmic_report.txt"
    generate_text_report(args.db, report_txt)

    total, surv_pct, surv_count, coverage, survivors = parse_text_report(report_txt)
    logging.info("Total jobs: %d", total)
    logging.info("Mutantes supervivientes: %d (%.2f%%)", surv_count, surv_pct)
    logging.info("Cobertura de mutación: %.2f%%", coverage)

    # Verificar umbral de cobertura
    if coverage < args.min_score:
        logging.error("Cobertura insuficiente: %.2f%% < %.2f%%", coverage, args.min_score)
        return 1

    # Generar MD si hay supervivientes
    if survivors:
        md_path = write_survivors_md(survivors, args.log_dir)
        logging.info("Survivors markdown generado: %s", md_path)

    logging.info("Mutation testing PASSED (>= %.2f%%)", args.min_score)
    return 0


if __name__ == "__main__":
    sys.exit(main())

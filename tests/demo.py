#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mutation_check.py

Orquesta pruebas de mutación con Cosmic Ray y genera:
  • mutating_testing_report.json – dump completo.
  • mutants_survived.json         – detalles de mutantes que sobrevivieron.
  • mutation_summary.md           – informe Markdown.
Sale con código 1 si la puntuación de mutación < --min-score.
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# ------- Configuración por defecto -------
DEFAULT_CONFIG   = Path(__file__).parent.parent / "config.toml"
DEFAULT_DB       = Path(__file__).parent.parent / "cr_session.sqlite"
DEFAULT_LOG_DIR  = Path(__file__).parent.parent / "logs"
DEFAULT_MIN_SCORE = 80.0  # % mínimo de mutantes “killed”

# -----------------------------------------

def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def run_command(cmd: List[str]) -> None:
    logging.info("Ejecutando: %s", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        logging.info(res.stdout.strip())
    if res.returncode != 0:
        logging.error("Error (exit %d): %s", res.returncode, res.stderr.strip())
        sys.exit(res.returncode)

def initialize_database(config: Path, db: Path) -> None:
    if not db.exists():
        logging.info("Inicializando base de datos: %s", db)
        run_command(["cosmic-ray", "init", str(config), str(db), "--force"])
    else:
        logging.info("Base de datos ya existe, continúa.")

def execute_mutations(config: Path, db: Path) -> None:
    run_command(["cosmic-ray", "exec", str(config), str(db)])

def dump_to_json(db: Path, out: Path) -> None:
    out.parent.mkdir(exist_ok=True, parents=True)
    logging.info("Volcando informe JSON: %s", out)
    with out.open("w", encoding="utf-8") as f:
        res = subprocess.run(["cosmic-ray", "dump", str(db)],
                             stdout=f, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        logging.error("Error al volcar JSON: %s", res.stderr.strip())
        sys.exit(res.returncode)

def parse_report(report: Path) -> List[Dict[str, Any]]:
    """
    Convierte el dump JSON de Cosmic Ray en una lista de jobs.
    Cada línea es un JSON (o lista de mutaciones), las unimos en una lista grande.
    """
    lines = []
    for ln in report.read_text(encoding="utf-8").splitlines():
        txt = ln.strip().rstrip(",")
        if txt and txt not in ("[", "]"):
            lines.append(txt)
    blob = "[" + ",".join(lines) + "]"
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as e:
        logging.error("No pude parsear el JSON: %s", e)
        sys.exit(1)

    # Normalizar: cada entry puede ser dict o lista de dicts
    jobs: List[Dict[str, Any]] = []
    for entry in data:
        if isinstance(entry, list):
            jobs.extend(entry)
        else:
            jobs.append(entry)
    return jobs

def calculate_metrics(jobs: List[Dict[str, Any]]) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    Cuenta total y killed, y recoge supervivientes.
    Devuelve: (killed, total, survivors)
    """
    total = 0
    killed = 0
    survivors: List[Dict[str, Any]] = []

    for job in jobs:
        job_id = job.get("job_id")
        mutations = job.get("mutations", [])
        # Para cada mutante:
        for m in mutations:
            total += 1
            # test_outcome puede venir en la mutación o en el job
            outcome = m.get("test_outcome") or job.get("test_outcome") or ""
            if outcome == "killed":
                killed += 1
            else:
                survivors.append({
                    "job_id":        job_id,
                    "module_path":   m.get("module_path"),
                    "operator_name": m.get("operator_name"),
                    "test_outcome":  outcome,
                    "output":        m.get("output") or job.get("output", ""),
                })

    return killed, total, survivors

def save_json(data: List[Dict[str, Any]], path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info("Guardado JSON (%d ítems): %s", len(data), path)

def save_markdown(killed: int, total: int,
                  survivors: List[Dict[str, Any]], log_dir: Path) -> Path:
    score = (killed / total * 100) if total else 0.0
    md = log_dir / "mutation_summary.md"
    lines: List[str] = [
        "# 🧪 Informe de Mutation Testing\n",
        f"- **Total de mutantes:** {total}",
        f"- **Killed:** {killed}",
        f"- **Sobrevivieron:** {len(survivors)}",
        f"- **Mutation Score:** {score:.1f}%\n",
    ]
    if survivors:
        lines += [
            "## ⚠️ Mutantes supervivientes\n",
            "| Job ID | File | Operador | Resultado del test | Output |",
            "| ------ | ---- | -------- | ------------------ | ------ |",
        ]
        for m in survivors:
            lines.append(
                f"| {m['job_id']} | {m['module_path']} | {m['operator_name']} "
                f"| {m['test_outcome']} | {m['output'].replace('|','\\|')} |"
            )
    else:
        lines.append("✅ **Todos los mutantes fueron muertos. ¡Genial!**")

    md.parent.mkdir(exist_ok=True, parents=True)
    md.write_text("\n".join(lines), encoding="utf-8")
    logging.info("Guardado reporte Markdown: %s", md)
    return md

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta Cosmic Ray, evalúa métricas y genera informe."
    )
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG,
                        help="Ruta a config.toml de Cosmic Ray")
    parser.add_argument("-d", "--db",     type=Path, default=DEFAULT_DB,
                        help="Ruta a la base SQLite de Cosmic Ray")
    parser.add_argument("-l", "--log-dir", type=Path, default=DEFAULT_LOG_DIR,
                        help="Directorio para salidas JSON y MD")
    parser.add_argument("-m", "--min-score", type=float, default=DEFAULT_MIN_SCORE,
                        help="%% mínimo de mutantes muertos para pasar")
    args = parser.parse_args()

    setup_logging()
    initialize_database(args.config, args.db)
    execute_mutations(args.config, args.db)

    report_json = args.log_dir / "mutating_testing_report.json"
    dump_to_json(args.db, report_json)

    jobs = parse_report(report_json)
    killed, total, survivors = calculate_metrics(jobs)

    # Guardar JSON y Markdown
    args.log_dir.mkdir(exist_ok=True, parents=True)
    if survivors:
        save_json(survivors, args.log_dir / "mutants_survived.json")
    save_markdown(killed, total, survivors, args.log_dir)

    # Mostrar resultado y salir con código adecuado
    score = (killed / total * 100) if total else 0.0
    logging.info("Mutation score: %.1f%% (%d/%d killed)", score, killed, total)
    if score < args.min_score:
        logging.error("❌ FALLÓ: mínimo %.1f%%, obtenido %.1f%%", args.min_score, score)
        return 1

    logging.info("✅ PASÓ (>= %.1f%%)", args.min_score)
    return 0

if __name__ == "__main__":
    sys.exit(main())

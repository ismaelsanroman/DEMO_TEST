#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mutation_check.py

Orquesta pruebas de mutación con Cosmic Ray y genera:
  • mutating_testing_report.json – dump completo (lo hace cosmic-ray).
  • mutants_survived.json         – mutantes que han sobrevivido ⚠️
  • mutation_summary.md           – informe Markdown con estadísticas.
Sale con código 1 si la tasa de mutantes “killed” < --min-score (%).
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# --- Valores por defecto ---
DEFAULT_CONFIG    = Path(__file__).parent.parent / "config.toml"
DEFAULT_DB        = Path(__file__).parent.parent / "cr_session.sqlite"
DEFAULT_LOG_DIR   = Path(__file__).parent.parent / "logs"
DEFAULT_MIN_SCORE = 80.0  # %

# -----------------------------
def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def run_command(cmd: List[str]) -> None:
    logging.info("▶ Ejecutando: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        logging.info(proc.stdout.strip())
    if proc.returncode != 0:
        logging.error("❌ Error (%d) en comando: %s", proc.returncode, proc.stderr.strip())
        sys.exit(proc.returncode)

def initialize_db(config: Path, db: Path) -> None:
    if not db.exists():
        logging.info("🔧 Inicializando BBDD: %s", db)
        run_command(["cosmic-ray", "init", str(config), str(db), "--force"])
    else:
        logging.info("ℹ️  BBDD ya existe, se omite init.")

def execute_mutations(config: Path, db: Path) -> None:
    run_command(["cosmic-ray", "exec", str(config), str(db)])

def dump_to_json(db: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    logging.info("💾 Volcando reporte JSON completo: %s", out)
    with out.open("w", encoding="utf-8") as f:
        proc = subprocess.run(["cosmic-ray", "dump", str(db)], stdout=f, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        logging.error("❌ Falló dump: %s", proc.stderr.strip())
        sys.exit(proc.returncode)

def parse_report(path: Path) -> List[Dict[str, Any]]:
    """
    Convierte el stream JSON de cosmic-ray en una lista hueca de mutantes.
    Maneja líneas sueltas o listas dentro de cada entry.
    """
    raw = path.read_text(encoding="utf-8").splitlines()
    lines = [l.strip().rstrip(",") for l in raw if l.strip() and l.strip() not in ("[", "]")]
    combined = "[" + ",".join(lines) + "]"
    try:
        data = json.loads(combined)
    except json.JSONDecodeError as e:
        logging.error("❌ Error parseando JSON: %s", e)
        sys.exit(1)

    # Aplanamos: cada elemento puede ser un dict (job) o lista (mutaciones)
    jobs: List[Dict[str, Any]] = []
    for entry in data:
        if isinstance(entry, dict):
            jobs.append(entry)
        elif isinstance(entry, list):
            # cada mutación de la lista la metemos como “job” individual
            for mut in entry:
                jobs.append(mut)
    return jobs

def calculate_metrics(jobs: List[Dict[str, Any]]) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    Recorre jobs, cuenta total vs killed y acumula los supervivientes con:
    job_id, module_path, operator_name, output y test_outcome.
    """
    total = 0
    killed = 0
    survivors: List[Dict[str, Any]] = []

    for job in jobs:
        # extraemos campos
        job_id  = job.get("job_id")
        # Si el entry es un job con lista de mutaciones:
        mutants = job.get("mutations") or [job] if "job_id" not in job else [job]
        # En cada mutante:
        for m in mutants:
            total += 1
            outcome = m.get("test_outcome") or job.get("test_outcome")
            if outcome == "killed":
                killed += 1
            else:
                survivors.append({
                    "job_id"        : job_id,
                    "module_path"   : m.get("module_path"),
                    "operator_name" : m.get("operator_name"),
                    "output"        : m.get("output") or job.get("output"),
                    "test_outcome"  : outcome or "unknown",
                })

    return killed, total, survivors

def save_survivors(survivors: List[Dict[str, Any]], out_json: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(survivors, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info("⚠️  Guardados %d mutantes supervivientes en %s", len(survivors), out_json)

def save_markdown_report(killed: int, total: int, survivors: List[Dict[str, Any]],
                         out_md: Path, min_score: float) -> None:
    score = (killed / total * 100) if total else 0.0
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 🧪 Mutation Testing Report\n",
        f"- **Total mutantes:** {total}",
        f"- **Killed:** {killed}",
        f"- **Supervivientes:** {len(survivors)}",
        f"- **Mutation Score:** {score:.1f}% (mínimo requerido: {min_score:.1f}%)\n",
    ]
    if survivors:
        lines += [
            "## ⚠️ Mutantes Supervivientes\n",
            "| Job ID | Módulo | Operador | Resultado |",
            "| ------ | ------ | -------- | --------- |",
        ]
        for m in survivors:
            lines.append(f"| {m['job_id']} | {m['module_path']} | {m['operator_name']} | {m['test_outcome']} |")
    else:
        lines.append("✅ **¡Todos los mutantes fueron killed! Buen trabajo.**")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    logging.info("📝 Informe Markdown guardado en %s", out_md)

def main() -> int:
    parser = argparse.ArgumentParser(description="Run mutation testing via Cosmic Ray and report survivors.")
    parser.add_argument("-c", "--config",   type=Path, default=DEFAULT_CONFIG,   help="Ruta a config.toml")
    parser.add_argument("-d", "--db",       type=Path, default=DEFAULT_DB,       help="Ruta a cr_session.sqlite")
    parser.add_argument("-l", "--log-dir",  type=Path, default=DEFAULT_LOG_DIR,  help="Directorio para outputs")
    parser.add_argument("-m", "--min-score",type=float, default=DEFAULT_MIN_SCORE,help="Kill rate mínimo (%)")
    args = parser.parse_args()

    setup_logging()
    initialize_db(args.config, args.db)
    execute_mutations(args.config, args.db)

    report_json = args.log_dir / "mutating_testing_report.json"
    dump_to_json(args.db, report_json)

    jobs      = parse_report(report_json)
    killed, total, survivors = calculate_metrics(jobs)

    # Guardamos JSON y Markdown
    save_survivors(survivors, args.log_dir / "mutants_survived.json")
    save_markdown_report(killed, total, survivors,
                         args.log_dir / "mutation_summary.md", args.min_score)

    logging.info("📊 Mutation score: %.1f%% (%d/%d killed)", (killed/total*100 if total else 0), killed, total)

    # Si no llega al umbral, salimos con error
    if total and (killed / total * 100) < args.min_score:
        logging.error("🚨 Mutation testing FAILED: mínimo %.1f%%, obtenido %.1f%%",
                      args.min_score, killed / total * 100)
        return 1

    logging.info("✅ Mutation testing PASSED (>= %.1f%%)", args.min_score)
    return 0

if __name__ == "__main__":
    sys.exit(main())

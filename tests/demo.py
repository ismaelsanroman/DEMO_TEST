#!/usr/bin/env python3
"""
mutation_check.py

Orquesta pruebas de mutación con Cosmic Ray y genera:
  • mutating_testing_report.json  – dump completo (lo hace cosmic-ray).
  • mutants_survived.json         – mutantes que han sobrevivido ⚠️
  • mutants_timeout.json          – mutantes que acabaron en timeout/exception ⏰
  • mutation_summary.md           – informe Markdown con estadísticas.
Saldrá con exit 1 si la puntuación de mutación < --min-score.
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# ---- configuración por defecto -------------------------------------------
DEFAULT_CONFIG   = Path(__file__).parent.parent / "config.toml"
DEFAULT_DB       = Path(__file__).parent.parent / "cr_session.sqlite"
DEFAULT_LOG_DIR  = Path(__file__).parent.parent / "logs"
DEFAULT_MIN_SCORE = 80.0

# ---------------------------------------------------------------------------
def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run_command(cmd: List[str]) -> None:
    logging.info("Running command: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        logging.info(result.stdout.strip())
    if result.returncode != 0:
        logging.error("Command failed (exit %d): %s", result.returncode, result.stderr.strip())
        sys.exit(result.returncode)


# ---------------------------------------------------------------------------
def initialize_database(config: Path, db: Path) -> None:
    if not db.exists():
        logging.info("Database not found, initializing: %s", db)
        run_command(["cosmic-ray", "init", str(config), str(db), "--force"])
    else:
        logging.info("Database already exists, skipping initialization.")


def execute_mutations(config: Path, db: Path) -> None:
    run_command(["cosmic-ray", "exec", str(config), str(db)])


def dump_to_json(db: Path, report: Path) -> None:
    report.parent.mkdir(parents=True, exist_ok=True)
    logging.info("Dumping full report to JSON: %s", report)
    with report.open("w", encoding="utf-8") as f:
        result = subprocess.run(
            ["cosmic-ray", "dump", str(db)],
            stdout=f,
            stderr=subprocess.PIPE,
            text=True
        )
    if result.returncode != 0:
        logging.error("Failed to dump report: %s", result.stderr.strip())
        sys.exit(result.returncode)


# ---------------------------------------------------------------------------
def parse_report(report: Path) -> List[Dict]:
    """Convierte el stream JSON de cosmic-ray en lista de jobs (dict)."""
    lines = [
        ln.strip().rstrip(",")
        for ln in report.read_text(encoding="utf-8").splitlines()
        if ln.strip() and ln.strip() not in ("[", "]")
    ]
    combined = "[" + ",".join(lines) + "]"
    try:
        data = json.loads(combined)
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON report: %s", e)
        return []

    jobs: List[Dict] = []
    for entry in data:
        jobs.extend(entry if isinstance(entry, list) else [entry])
    return jobs


# ---------------------------------------------------------------------------
def calculate_metrics(jobs: List[Dict]) -> Tuple[int, int, List[Dict], List[Dict]]:
    """
    Devuelve:
        killed, total, survivors (≠killed), timeouts (timeout/exception)
    """
    total = killed = 0
    survivors: List[Dict] = []
    timeouts:  List[Dict] = []

    for job in jobs:
        job_id  = job.get("job_id")
        mutants = job.get("mutations", [])

        for m in mutants:
            total += 1
            outcome = m.get("test_outcome") or job.get("test_outcome")

            if outcome == "killed":
                killed += 1
                continue  # nada más que hacer

            entry = {
                "job_id":         job_id,
                "module_path":    m.get("module_path"),
                "operator_name":  m.get("operator_name"),
                "occurrence":     m.get("occurrence"),
                "test_outcome":   outcome or "timeout",
                "worker_outcome": m.get("worker_outcome"),
                "output":         m.get("output") or job.get("output"),
                "diff":           m.get("diff"),
            }

            wo  = (entry["worker_outcome"] or "").lower()
            out = (entry["output"] or "").lower()
            if entry["test_outcome"] == "timeout" or "timeout" in out or "exception" in wo:
                timeouts.append(entry)
            else:
                survivors.append(entry)

    return killed, total, survivors, timeouts


# ---------------------------------------------------------------------------
def save_survivors(data: List[Dict], path: Path) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logging.info("Saved %d entries to %s", len(data), path)


def save_markdown_report(killed: int, total: int,
                         survivors: List[Dict], timeouts: List[Dict],
                         log_dir: Path) -> Path:
    score  = (killed / total) * 100 if total else 0.0
    md_path = log_dir / "mutation_summary.md"

    lines = [
        "# Mutation Testing Report\n",
        f"- **Total mutants:** {total}",
        f"- **Killed:** {killed}",
        f"- **Survived:** {len(survivors)}",
        f"- **Timeouts:** {len(timeouts)}",
        f"- **Mutation Score:** {score:.1f}%\n",
    ]

    if survivors:
        lines += [
            "## ⚠️ Survived Mutants\n",
            "| Job_ID | File | Operator |",
            "| ------ | ---- | -------- |",
        ]
        for m in survivors:
            lines.append(f"| {m['job_id']} | {m['module_path']} | {m['operator_name']} |")

    if timeouts:
        lines += [
            "\n## ⏰ Timeout/Exception Mutants\n",
            "| Job_ID | File | Operator |",
            "| ------ | ---- | -------- |",
        ]
        for m in timeouts:
            lines.append(f"| {m['job_id']} | {m['module_path']} | {m['operator_name']} |")

    if not survivors and not timeouts:
        lines.append("✅ **All mutants killed. Great job!**")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    logging.info("Markdown summary saved to %s", md_path)
    return md_path


# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Run mutation testing via Cosmic Ray and report survivors.")
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG,
                        help="Path to the Cosmic Ray config.toml")
    parser.add_argument("-d", "--db", type=Path, default=DEFAULT_DB,
                        help="Path to the Cosmic Ray SQLite database")
    parser.add_argument("-l", "--log-dir", type=Path, default=DEFAULT_LOG_DIR,
                        help="Directory for JSON report outputs")
    parser.add_argument("-m", "--min-score", type=float, default=DEFAULT_MIN_SCORE,
                        help="Minimum kill rate (%) to consider the test suite passing")
    args = parser.parse_args()

    setup_logging()
    initialize_database(args.config, args.db)
    execute_mutations(args.config, args.db)

    report_file = args.log_dir / "mutating_testing_report.json"
    dump_to_json(args.db, report_file)

    jobs = parse_report(report_file)
    killed, total, survivors, timeouts = calculate_metrics(jobs)

    args.log_dir.mkdir(parents=True, exist_ok=True)
    if survivors:
        save_survivors(survivors, args.log_dir / "mutants_survived.json")
    if timeouts:
        save_survivors(timeouts, args.log_dir / "mutants_timeout.json")

    save_markdown_report(killed, total, survivors, timeouts, args.log_dir)

    score = (killed / total) * 100 if total else 0.0
    logging.info("Mutation score: %.1f%% (%d/%d killed)", score, killed, total)

    if score < args.min_score:
        logging.error("Mutation testing FAILED: minimum %.1f%%, obtained %.1f%%",
                      args.min_score, score)
        return 1

    logging.info("Mutation testing PASSED (>= %.1f%%)", args.min_score)
    return 0


if __name__ == "__main__":
    sys.exit(main())

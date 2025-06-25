#!/usr/bin/env python3
"""
mutation_check.py

This script orchestrates mutation testing using Cosmic Ray. It:
1. Initializes the Cosmic Ray database if not already present.
2. Executes the mutation testing session.
3. Dumps the full session to a JSON file.
4. Parses the JSON report (including nested arrays or NDJSON) into a flat list of jobs.
5. Computes mutation metrics: total mutants, killed, survivors.
6. Writes surviving mutants to JSON.
7. Generates a Markdown summary report.
8. Exits with failure if the mutation score is below the configured threshold.
"""

import sys
import json
import logging
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Any

# Default paths and thresholds
DEFAULT_CONFIG = Path(__file__).parent.parent / "config.toml"
DEFAULT_DB = Path(__file__).parent.parent / "cr_session.sqlite"
DEFAULT_LOG_DIR = Path(__file__).parent.parent / "logs"
DEFAULT_MIN_SCORE = 80.0  # minimum acceptable kill rate (%)


def setup_logging() -> None:
    """Configure basic logging format and level."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run_command(cmd: List[str]) -> None:
    """
    Execute a system command, log its output, and abort on failure.

    Args:
        cmd: List of command-line arguments.
    """
    logging.info("Running command: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        logging.info(result.stdout.strip())
    if result.returncode != 0:
        logging.error("Command failed (exit %d): %s", result.returncode, result.stderr.strip())
        sys.exit(result.returncode)


def initialize_database(config: Path, db: Path) -> None:
    """
    Initialize the Cosmic Ray database if it does not exist.

    Args:
        config: Path to the Cosmic Ray TOML configuration.
        db: Path to the SQLite database file.
    """
    if not db.exists():
        logging.info("Database not found, initializing: %s", db)
        run_command(["cosmic-ray", "init", str(config), str(db), "--force"])
    else:
        logging.info("Database already exists, skipping initialization.")


def execute_mutations(config: Path, db: Path) -> None:
    """
    Execute the mutation testing session.

    Args:
        config: Path to the Cosmic Ray TOML configuration.
        db: Path to the SQLite database file.
    """
    run_command(["cosmic-ray", "exec", str(config), str(db)])


def dump_to_json(db: Path, report: Path) -> None:
    """
    Dump the full Cosmic Ray session to a JSON file.

    Args:
        db: Path to the SQLite database file.
        report: Path where the JSON report will be saved.
    """
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


def parse_report(report: Path) -> List[Dict[str, Any]]:
    """
    Parse the Cosmic Ray JSON dump into a flat list of job dictionaries.
    This handles:
      - A single JSON array of jobs.
      - A nested array ([[ ... ]]).
      - Line-delimited JSON (NDJSON) with optional commas.
    """
    text = report.read_text(encoding="utf-8")
    lines = text.splitlines()
    jobs: List[Any] = []

    for line in lines:
        stripped = line.strip().rstrip(',')
        # skip empty lines or bracket markers
        if not stripped or stripped in ('[', ']'):
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as e:
            logging.warning("Skipped invalid JSON line: %s", e)
            continue
        jobs.append(obj)

    # Flatten if any entry is itself a list of jobs
    flat_jobs: List[Dict[str, Any]] = []
    for entry in jobs:
        if isinstance(entry, list):
            for sub in entry:
                if isinstance(sub, dict):
                    flat_jobs.append(sub)
        elif isinstance(entry, dict):
            flat_jobs.append(entry)
        else:
            logging.warning("Unexpected entry type in jobs: %r", entry)

    logging.info("Parsed %d job(s) from report", len(flat_jobs))
    return flat_jobs


def calculate_metrics(jobs: List[Dict[str, Any]]) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    Compute killed count, total mutants, and collect surviving mutants.

    Each job['mutations'] is actually a flat list of two dicts per mutant:
    - the first dict: metadata (module_path, operator_name, occurrence…)
    - the second dict: result (worker_outcome, test_outcome, diff…)

    We iterate en pasos de 2 para procesar cada par.
    """
    total = 0
    killed = 0
    survivors: List[Dict[str, Any]] = []

    for job in jobs:
        muts = job.get("mutations", [])
        # iterate en pares: [meta0, res0, meta1, res1, …]
        for i in range(0, len(muts), 2):
            meta = muts[i]
            result = muts[i+1] if i+1 < len(muts) else {}
            total += 1

            outcome = result.get("test_outcome")
            if outcome == "killed":
                killed += 1
            else:
                # sólo añado a survivors si tengo al menos la metadata
                if meta.get("module_path") or meta.get("operator_name") is not None:
                    survivors.append({
                        "module_path": meta.get("module_path"),
                        "operator_name": meta.get("operator_name"),
                        "occurrence": meta.get("occurrence"),
                        "test_outcome": outcome,
                        "worker_outcome": result.get("worker_outcome"),
                        "output": result.get("output"),
                        "diff": result.get("diff"),
                    })

    logging.info("Metrics computed: %d total, %d killed, %d survived", total, killed, len(survivors))
    return killed, total, survivors
    

def save_survivors(survivors: List[Dict[str, Any]], log_dir: Path) -> None:
    """
    Write the surviving mutants to a JSON file.

    Args:
        survivors: list of surviving mutant dicts.
        log_dir: directory where the file will be created.
    """
    output_path = log_dir / "mutants_survived.json"
    log_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(survivors, indent=2), encoding="utf-8")
    logging.info("Saved %d surviving mutants to %s", len(survivors), output_path)


def save_markdown_summary(killed: int, total: int, survivors: List[Dict[str, Any]], log_dir: Path) -> None:
    """
    Generate a Markdown summary of the mutation testing results.

    Args:
        killed: number of killed mutants.
        total: total mutants.
        survivors: list of surviving mutants.
        log_dir: directory where the Markdown file will be created.
    """
    score = (killed / total) * 100 if total else 0.0
    md_lines = [
        "# Mutation Testing Report",
        "",
        f"- **Total mutants**: {total}",
        f"- **Killed**: {killed}",
        f"- **Survived**: {total - killed}",
        f"- **Mutation Score**: {score:.1f}%",
        "",
        "## Surviving Mutants",
        "",
        "| File | Operator | Outcome |",
        "|------|----------|---------|",
    ]
    for s in survivors:
        md_lines.append(f"| `{s['module_path']}` | `{s['operator_name']}` | `{s['test_outcome']}` |")

    md_path = log_dir / "mutation_summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    logging.info("Markdown summary saved to %s", md_path)


def main() -> int:
    """
    Main entry point: parse args, run mutation workflow, and report metrics.
    """
    parser = argparse.ArgumentParser(description="Run mutation testing via Cosmic Ray and produce reports.")
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG,
                        help="Path to the Cosmic Ray config.toml")
    parser.add_argument("-d", "--db", type=Path, default=DEFAULT_DB,
                        help="Path to the Cosmic Ray SQLite database")
    parser.add_argument("-l", "--log-dir", type=Path, default=DEFAULT_LOG_DIR,
                        help="Directory for JSON and Markdown outputs")
    parser.add_argument("-m", "--min-score", type=float, default=DEFAULT_MIN_SCORE,
                        help="Minimum kill rate (%) to pass")

    args = parser.parse_args()
    setup_logging()

    initialize_database(args.config, args.db)
    execute_mutations(args.config, args.db)

    report_file = args.log_dir / "mutating_testing_report.json"
    dump_to_json(args.db, report_file)

    jobs = parse_report(report_file)
    killed, total, survivors = calculate_metrics(jobs)

    if survivors:
        save_survivors(survivors, args.log_dir)
    save_markdown_summary(killed, total, survivors, args.log_dir)

    score = (killed / total) * 100 if total else 0.0
    logging.info("Final mutation score: %.1f%% (%d/%d killed)", score, killed, total)

    if score < args.min_score:
        logging.error("Mutation testing FAILED: required %.1f%%, got %.1f%%", args.min_score, score)
        return 1

    logging.info("Mutation testing PASSED (>= %.1f%%)", args.min_score)
    return 0


if __name__ == "__main__":
    sys.exit(main())

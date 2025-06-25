#!/usr/bin/env python3
"""
mutation_check.py

This script orchestrates mutation testing using Cosmic Ray. It:
1. Initializes the Cosmic Ray database if not already present.
2. Executes the mutation testing session.
3. Dumps the full session to a JSON file.
4. Parses the JSON report to compute metrics.
5. Saves the list of surviving mutants to a separate JSON.
6. Generates a Markdown summary report.
7. Calculates and prints the mutation score, failing if below threshold.
"""

import sys
import json
import logging
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

# Default configuration paths and thresholds
DEFAULT_CONFIG = Path(__file__).parent.parent / "config.toml"
DEFAULT_DB = Path(__file__).parent.parent / "cr_session.sqlite"
DEFAULT_LOG_DIR = Path(__file__).parent.parent / "logs"
DEFAULT_MIN_SCORE = 80.0  # minimum acceptable mutation score (%)


def setup_logging() -> None:
    """
    Configure basic logging format and level.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run_command(cmd: List[str]) -> None:
    """
    Execute a system command and abort on failure.

    Args:
        cmd: List of command arguments to execute.
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


def parse_report(report: Path) -> List[Dict]:
    """
    Read any variant of JSON (plain array, nested array, or NDJSON)
    and extract all mutation jobs into a flat list of dicts.

    Args:
        report: Path to the dumped JSON report.

    Returns:
        A list of job dictionaries, each containing 'job_id' and 'mutations'.
    """
    text = report.read_text(encoding="utf-8").strip()
    # First attempt: parse as standard JSON
    try:
        data = json.loads(text)
        # Case: nested array [[...]]
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
            return data[0]
        # Case: flat array of job dicts
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Fallback: incremental parsing of NDJSON or malformed JSON arrays
    jobs: List[Dict] = []
    decoder = json.JSONDecoder()
    idx = 0
    length = len(text)

    # skip leading '[' if present
    if idx < length and text[idx] == "[":
        idx += 1

    # parse one JSON object at a time
    while idx < length:
        # skip whitespace and commas
        while idx < length and text[idx] in " \r\n\t,":
            idx += 1
        if idx >= length or text[idx] == "]":
            break
        try:
            obj, consumed = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError as e:
            logging.warning("Could not parse JSON at position %d: %s", idx, e)
            break
        # if it's a dict, add directly
        if isinstance(obj, dict):
            jobs.append(obj)
        # if it's a list, unpack any dict entries
        elif isinstance(obj, list):
            for entry in obj:
                if isinstance(entry, dict):
                    jobs.append(entry)
        idx += consumed

    return jobs


def calculate_metrics(jobs: List[Dict]) -> Tuple[int, int, List[Dict]]:
    """
    Compute the number of killed mutants and collect surviving mutants.

    Args:
        jobs: List of job dictionaries from parse_report().

    Returns:
        A tuple (killed_count, total_mutants, survivors_list).
    """
    total = 0
    killed = 0
    survivors: List[Dict] = []

    for job in jobs:
        mutations = job.get("mutations") or []
        if not isinstance(mutations, list):
            continue
        total += len(mutations)
        for m in mutations:
            outcome = m.get("test_outcome")
            if outcome == "killed":
                killed += 1
            else:
                # include only if it has at least one non-null key
                if any(m.get(k) for k in ("module_path", "operator_name", "occurrence")):
                    survivors.append({
                        "module_path": m.get("module_path"),
                        "operator_name": m.get("operator_name"),
                        "occurrence": m.get("occurrence"),
                        "test_outcome": outcome,
                        "worker_outcome": m.get("worker_outcome"),
                        "output": m.get("output"),
                        "diff": m.get("diff"),
                    })

    return killed, total, survivors


def save_survivors(survivors: List[Dict], log_dir: Path) -> Path:
    """
    Write the list of surviving mutants to a JSON file.

    Args:
        survivors: List of surviving mutant dictionaries.
        log_dir: Directory where the output will be saved.

    Returns:
        Path to the saved JSON file.
    """
    output_path = log_dir / "mutants_survived.json"
    log_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(survivors, indent=2), encoding="utf-8")
    logging.info("Saved %d surviving mutants to %s", len(survivors), output_path)
    return output_path


def save_markdown_summary(killed: int, total: int, survivors: List[Dict], log_dir: Path) -> None:
    """
    Generate a Markdown summary report of mutation testing.

    Args:
        killed: Number of killed mutants.
        total: Total number of mutants.
        survivors: List of surviving mutants.
        log_dir: Directory where the Markdown file will be saved.
    """
    md_file = log_dir / "mutation_summary.md"
    score = (killed / total) * 100 if total else 0.0

    lines = [
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
        lines.append(f"| `{s['module_path']}` | `{s['operator_name']}` | `{s['test_outcome']}` |")

    md_file.write_text("\n".join(lines), encoding="utf-8")
    logging.info("Markdown summary saved to %s", md_file)


def main() -> int:
    """
    Main entry point: parse arguments, run the mutation workflow, and report metrics.
    """
    parser = argparse.ArgumentParser(
        description="Run mutation testing via Cosmic Ray and produce reports."
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
        help="Directory for JSON and Markdown report outputs"
    )
    parser.add_argument(
        "--min-score", "-m", type=float, default=DEFAULT_MIN_SCORE,
        help="Minimum kill rate (%) to consider the test suite passing"
    )
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
    logging.info("Mutation score: %.1f%% (%d/%d killed)", score, killed, total)

    if score < args.min_score:
        logging.error(
            "Mutation testing FAILED: minimum %.1f%% required, obtained %.1f%%",
            args.min_score, score
        )
        return 1

    logging.info("Mutation testing PASSED (>= %.1f%%)", args.min_score)
    return 0


if __name__ == "__main__":
    sys.exit(main())

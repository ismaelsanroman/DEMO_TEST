#!/usr/bin/env python3
import sys
import json
import logging
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

DEFAULT_CONFIG = Path(__file__).parent.parent / "config.toml"
DEFAULT_DB = Path(__file__).parent.parent / "cr_session.sqlite"
DEFAULT_LOG_DIR = Path(__file__).parent.parent / "logs"
DEFAULT_MIN_SCORE = 80.0

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
        result = subprocess.run(["cosmic-ray", "dump", str(db)], stdout=f, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logging.error("Failed to dump report: %s", result.stderr.strip())
        sys.exit(result.returncode)

def parse_report(report: Path) -> List[Dict]:
    jobs: List[Dict] = []
    for line in report.read_text(encoding="utf-8").splitlines():
        line = line.strip().rstrip(",")
        if line and not line.startswith("[") and not line.endswith("]"):
            try:
                jobs.append(json.loads(line))
            except json.JSONDecodeError as e:
                logging.warning("Skipped invalid JSON line: %s", e)
    return jobs

def calculate_metrics(jobs: List[Dict]) -> Tuple[int, int, List[Dict]]:
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
                # Añadir solo si tiene al menos un dato útil
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
    output_path = log_dir / "mutants_survived.json"
    log_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(survivors, indent=2), encoding="utf-8")
    logging.info("Saved %d surviving mutants to %s", len(survivors), output_path)
    return output_path

def save_markdown_summary(killed: int, total: int, survivors: List[Dict], log_dir: Path) -> None:
    md_file = log_dir / "mutation_summary.md"
    score = (killed / total) * 100 if total else 0.0

    lines = [
        "# ☠️ Mutation Testing Report",
        "",
        f"- **Total mutants**: {total}",
        f"- **Killed**: {killed}",
        f"- **Survived**: {total - killed}",
        f"- **Mutation Score**: {score:.1f}%",
        "",
        "## 🧬 Surviving Mutants",
        "",
        "| File | Operator | Outcome |",
        "|------|----------|---------|",
    ]

    for s in survivors:
        lines.append(f"| `{s['module_path']}` | `{s['operator_name']}` | `{s['test_outcome']}` |")

    md_file.write_text("\n".join(lines), encoding="utf-8")
    logging.info("Markdown summary saved to %s", md_file)

def main() -> int:
    parser = argparse.ArgumentParser(description="Run mutation testing via Cosmic Ray and report survivors.")
    parser.add_argument("--config", "-c", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--db", "-d", type=Path, default=DEFAULT_DB)
    parser.add_argument("--log-dir", "-l", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--min-score", "-m", type=float, default=DEFAULT_MIN_SCORE)
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
        logging.error("Mutation testing FAILED: minimum %.1f%%, obtained %.1f%%", args.min_score, score)
        return 1

    logging.info("Mutation testing PASSED (>= %.1f%%)", args.min_score)
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mutation_check.py

Orquesta las pruebas de mutación con Cosmic Ray y genera:
  • mutating_testing_report.json – volcado completo.
  • mutants_survived.json         – detalles de mutantes supervivientes.
  • mutation_summary.md           – informe Markdown.
Sale con código 1 si el porcentaje de mutantes “killed” es inferior al umbral.
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Configuración por defecto
DEFAULT_CONFIG    = Path(__file__).parent.parent / "config.toml"
DEFAULT_DB        = Path(__file__).parent.parent / "cr_session.sqlite"
DEFAULT_LOG_DIR   = Path(__file__).parent.parent / "logs"
DEFAULT_MIN_SCORE = 80.0  # porcentaje mínimo de mutantes eliminados

def configurar_registro() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def ejecutar_comando(cmd: List[str]) -> None:
    logging.info("Ejecutando: %s", " ".join(cmd))
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.stdout:
        logging.info(resultado.stdout.strip())
    if resultado.returncode != 0:
        logging.error("Error (exit %d): %s", resultado.returncode, resultado.stderr.strip())
        sys.exit(resultado.returncode)

def inicializar_base_datos(config: Path, db: Path) -> None:
    if not db.exists():
        logging.info("Inicializando base de datos: %s", db)
        ejecutar_comando(["cosmic-ray", "init", str(config), str(db), "--force"])
    else:
        logging.info("La base de datos ya existe, se omite inicialización.")

def ejecutar_mutaciones(config: Path, db: Path) -> None:
    ejecutar_comando(["cosmic-ray", "exec", str(config), str(db)])

def volcar_json(db: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    logging.info("Volcando informe JSON en: %s", destino)
    with destino.open("w", encoding="utf-8") as f:
        resultado = subprocess.run(
            ["cosmic-ray", "dump", str(db)],
            stdout=f, stderr=subprocess.PIPE, text=True
        )
    if resultado.returncode != 0:
        logging.error("Error al volcar JSON: %s", resultado.stderr.strip())
        sys.exit(resultado.returncode)

def parsear_elementos(report: Path) -> List[Dict[str,Any]]:
    """
    Lee línea a línea el JSON volcado, descarta corchetes y comas,
    y devuelve la lista de objetos.
    """
    elementos = []
    for linea in report.read_text(encoding="utf-8").splitlines():
        txt = linea.strip().rstrip(",")
        if not txt or txt in ("[", "]"):
            continue
        elementos.append(json.loads(txt))
    return elementos

def extraer_mutaciones(items: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    """
    Empareja cada descriptor de mutante con su resultado:
      [descriptor, resultado, descriptor, resultado, …]
    y crea un registro único por mutante.
    """
    mutantes: List[Dict[str,Any]] = []
    i = 0
    while i < len(items):
        desc = items[i]
        if "module_path" not in desc:
            i += 1
            continue
        res = items[i+1] if i+1 < len(items) and "test_outcome" in items[i+1] else {}
        mutantes.append({
            "job_id":         desc.get("job_id"),
            "module_path":    desc.get("module_path"),
            "operator_name":  desc.get("operator_name"),
            "occurrence":     desc.get("occurrence"),
            "test_outcome":   res.get("test_outcome", ""),
            "worker_outcome": res.get("worker_outcome", ""),
            "output":         res.get("output", "").replace("\n","\\n"),
            "diff":           res.get("diff", "").replace("\n","\\n"),
        })
        i += 2
    return mutantes

def calcular_metricas(mutantes: List[Dict[str,Any]]) -> Tuple[int,int,List[Dict[str,Any]]]:
    total = len(mutantes)
    muertos = sum(1 for m in mutantes if m["test_outcome"] == "killed")
    supervivientes = [m for m in mutantes if m["test_outcome"] != "killed"]
    return muertos, total, supervivientes

def guardar_json(data: List[Dict[str,Any]], path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info("Guardado JSON con %d entradas en: %s", len(data), path)

def guardar_markdown(muertos: int, total: int,
                     supervivientes: List[Dict[str,Any]],
                     log_dir: Path) -> Path:
    porcentaje = (muertos / total * 100) if total else 0.0
    md_path = log_dir / "mutation_summary.md"
    lineas: List[str] = [
        "# Informe de Mutation Testing",
        "",
        f"- Total de mutantes: {total}",
        f"- Mutantes “killed”: {muertos}",
        f"- Mutantes supervivientes: {len(supervivientes)}",
        f"- Puntuación de mutación: {porcentaje:.1f}%",
        "",
    ]
    if supervivientes:
        lineas += [
            "## Mutantes supervivientes",
            "| job_id | archivo | operador | resultado del test | output |",
            "| ------ | ------- | -------- | ------------------ | ------ |",
        ]
        for m in supervivientes:
            out = m["output"].replace("|", "\\|")
            lineas.append(
                f"| {m['job_id']} | {m['module_path']} | {m['operator_name']} "
                f"| {m['test_outcome']} | {out} |"
            )
    else:
        lineas.append("Todos los mutantes fueron eliminados. ¡Éxito!")

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lineas), encoding="utf-8")
    logging.info("Guardado Markdown en: %s", md_path)
    return md_path

def main() -> int:
    parser = argparse.ArgumentParser(description="Pruebas de mutación con Cosmic Ray")
    parser.add_argument("-c", "--config",   type=Path,   default=DEFAULT_CONFIG,
                        help="Ruta al config.toml de Cosmic Ray")
    parser.add_argument("-d", "--db",       type=Path,   default=DEFAULT_DB,
                        help="Ruta a la base de datos SQLite de Cosmic Ray")
    parser.add_argument("-l", "--log-dir",  type=Path,   default=DEFAULT_LOG_DIR,
                        help="Directorio para salidas JSON y Markdown")
    parser.add_argument("-m", "--min-score",type=float, default=DEFAULT_MIN_SCORE,
                        help="Porcentaje mínimo de mutantes eliminados para pasar")
    args = parser.parse_args()

    configurar_registro()
    inicializar_base_datos(args.config, args.db)
    ejecutar_mutaciones(args.config, args.db)

    informe_json = args.log_dir / "mutating_testing_report.json"
    volcar_json(args.db, informe_json)

    elementos = parsear_elementos(informe_json)
    mutantes = extraer_mutaciones(elementos)
    muertos, total, supervivientes = calcular_metricas(mutantes)

    args.log_dir.mkdir(parents=True, exist_ok=True)
    if supervivientes:
        guardar_json(supervivientes, args.log_dir / "mutants_survived.json")
    guardar_markdown(muertos, total, supervivientes, args.log_dir)

    puntuacion = (muertos / total * 100) if total else 0.0
    logging.info("Puntuación de mutación: %.1f%% (%d/%d)", puntuacion, muertos, total)
    if puntuacion < args.min_score:
        logging.error("FALLÓ: se requiere al menos %.1f%%, obtenido %.1f%%",
                      args.min_score, puntuacion)
        return 1

    logging.info("APROBADO (>= %.1f%%)", args.min_score)
    return 0

if __name__ == "__main__":
    sys.exit(main())

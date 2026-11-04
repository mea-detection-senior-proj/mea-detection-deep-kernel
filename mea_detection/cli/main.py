"""Compose supported operations without exposing internal training stages."""
import argparse
from pathlib import Path
import sys

from .run import parse_config


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="Model extraction traffic detection")
    parser.add_argument("operation", choices=("run", "audit", "prepare", "report"))
    if not argv or argv[0] in ("-h", "--help"):
        parser.print_help()
        return
    operation = parser.parse_args(argv[:1]).operation
    try:
        if operation in ("run", "prepare"):
            operation_parser, config, dry_run = parse_config(argv[1:])
            if operation == "run" or dry_run:
                from mea_detection.experiments.workflow import execute
                return execute(config, dry_run=dry_run)
            from mea_detection.experiments.locked import prepare
            return prepare(config, config["output"])
        operation_parser = argparse.ArgumentParser(prog=f"{parser.prog} {operation}")
        operation_parser.add_argument("--output", required=True, type=Path)
        if operation == "report":
            operation_parser.add_argument("--runs", nargs="+", required=True, type=Path)
        else:
            operation_parser.add_argument("--data-root", type=Path, default=Path("data"))
        args = operation_parser.parse_args(argv[1:])
        if operation == "report":
            from mea_detection.reporting.comparison import summarize
            return summarize(args.runs, args.output)
        from mea_detection.data.readiness import audit
        from mea_detection.paths import project_path
        return audit(project_path(args.output), data_root=project_path(args.data_root))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

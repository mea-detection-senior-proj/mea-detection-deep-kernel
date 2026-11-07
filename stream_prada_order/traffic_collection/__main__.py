"""Offline-only CLI. Intentionally no collect, download, serve or enable command."""
import argparse
import json
from pathlib import Path

from .adapters import QwenLocalAdapter
from .audit import audit
from .collector import recover
from .schema import IntegrityError, require, strict_json, validate_manifest
from .store import EventStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("describe-qwen")
    manifest_command = commands.add_parser("validate-manifest")
    manifest_command.add_argument("--path", type=Path, required=True)
    for name in ["audit", "validate", "recover"]:
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = {"implementation": "phase-g-offline-v1", "real_execution_enabled": False,
                      "private_stores_scanned": False, "real_horizon256_feasibility": "unmeasured_no_authorized_data"}
        elif args.command == "describe-qwen":
            result = QwenLocalAdapter().deployment_plan()
        elif args.command == "validate-manifest":
            with args.path.open("rb") as source:
                raw = source.read(65537)
            require(len(raw) <= 65536, "manifest_too_large")
            manifest = strict_json(raw)
            validate_manifest(manifest)
            result = {"status": "valid", "traffic_kind": manifest["traffic_kind"],
                      "validation": "schema_and_references_only_not_authorization_certification",
                      "real_execution_enabled": False}
        elif args.command in ["audit", "validate"]:
            result = audit(args.root)
        else:
            require((args.root / "events.sqlite3").is_file(), "store_missing")
            with EventStore(args.root) as store:
                result = {"status": "recovered_without_resend", **recover(store)}
        print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
        return 0
    except IntegrityError as exc:
        print(json.dumps({"status": "invalid", "code": str(exc)}))
        return 2
    except Exception:
        # Exception messages may contain private paths, contents or credentials.
        print(json.dumps({"status": "invalid", "code": "operation_failed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

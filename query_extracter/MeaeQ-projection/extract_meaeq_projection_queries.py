#!/usr/bin/env python3
"""Extract MeaeQ SST-2 projection attack and normal query texts."""

from __future__ import annotations

import argparse
import json
import pickletools
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_ROOT = PROJECT_ROOT / "raw_data/MeaeQ-projection"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data/Meaeq_SST-2_projection"


def _memo_put(memo: dict[int, Any], last: Any, index: int | None = None) -> None:
    if index is None:
        index = len(memo)
    memo[index] = last


def read_string_list_pickle(path: Path) -> list[str]:
    stack: list[Any] = []
    marks: list[int] = []
    memo: dict[int, Any] = {}
    last: Any = None

    with path.open("rb") as src:
        for op, arg, pos in pickletools.genops(src):
            name = op.name
            if name in {"PROTO", "FRAME", "STOP"}:
                continue
            if name == "EMPTY_LIST":
                last = []
                stack.append(last)
            elif name == "MARK":
                marks.append(len(stack))
            elif name in {"BINUNICODE", "SHORT_BINUNICODE", "UNICODE"}:
                last = arg
                stack.append(last)
            elif name == "APPENDS":
                if not marks:
                    raise ValueError(f"APPENDS without MARK in {path} at {pos}")
                mark_index = marks.pop()
                items = stack[mark_index:]
                del stack[mark_index:]
                if not stack or not isinstance(stack[-1], list):
                    raise ValueError(f"APPENDS target is not a list in {path} at {pos}")
                stack[-1].extend(items)
                last = stack[-1]
            elif name in {"BINPUT", "LONG_BINPUT", "PUT"}:
                _memo_put(memo, last, int(arg))
            elif name == "MEMOIZE":
                _memo_put(memo, last)
            elif name in {"BINGET", "LONG_BINGET", "GET"}:
                last = memo[int(arg)]
                stack.append(last)
            else:
                raise ValueError(f"Unsupported pickle opcode {name} in {path} at {pos}")

    if len(stack) != 1 or not isinstance(stack[0], list):
        raise ValueError(f"Expected one list object in {path}, got stack {stack!r}")
    if not all(isinstance(item, str) for item in stack[0]):
        raise ValueError(f"Expected list[str] in {path}")
    return stack[0]


def write_queries(texts: list[str], output_path: Path, split_name: str) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as dst:
        for index, text in enumerate(texts):
            record = {
                "id": f"MeaeQ-SST-2-projection-{split_name}-{index}",
                "index": index,
                "query": text,
            }
            dst.write(json.dumps(record, ensure_ascii=False) + "\n")

    return len(texts)


def extract_queries(input_root: Path, output_root: Path) -> list[tuple[str, int, Path]]:
    files = {
        "attacker": input_root / "attack_query/query_content.pickle",
        "normal": input_root / "normal_query/query_content_merged.pickle",
    }
    results: list[tuple[str, int, Path]] = []

    for split_name, input_path in files.items():
        texts = read_string_list_pickle(input_path)
        output_path = output_root / split_name / "queries.jsonl"
        count = write_queries(texts, output_path, split_name)
        results.append((split_name, count, output_path))

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract MeaeQ SST-2 projection queries to JSONL."
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=DEFAULT_INPUT_ROOT,
        help=f"Input root. Default: {DEFAULT_INPUT_ROOT}",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Output root. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = extract_queries(args.input_root, args.output_root)
    for split_name, count, output_path in results:
        print(f"{split_name}: wrote {count} queries to {output_path}")


if __name__ == "__main__":
    main()

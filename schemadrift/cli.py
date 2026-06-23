"""Command-line interface for schema-drift.

Workflow:
    # 1. Snapshot the current schema of a dataset
    schema-drift snapshot data.json --name orders

    # 2. Later, check a new version of the data against the snapshot
    schema-drift check data_new.json --name orders

`check` exits non-zero if any BREAKING change is detected — drop it into CI to
enforce data contracts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    diff_schemas,
    infer_schema_from_csv,
    infer_schema_from_json,
)

SNAPSHOT_DIR = Path(".schema-drift")


def _infer(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".csv":
        return infer_schema_from_csv(text)
    return infer_schema_from_json(text)


def _snapshot_path(name: str) -> Path:
    return SNAPSHOT_DIR / f"{name}.schema.json"


def cmd_snapshot(args) -> int:
    schema = _infer(Path(args.data))
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    path = _snapshot_path(args.name)
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Snapshot saved: {path} ({len(schema)} columns)")
    return 0


def cmd_check(args) -> int:
    snap_path = _snapshot_path(args.name)
    if not snap_path.exists():
        print(f"No snapshot named '{args.name}'. Run `schema-drift snapshot` first.",
              file=sys.stderr)
        return 2

    old = json.loads(snap_path.read_text(encoding="utf-8"))
    new = _infer(Path(args.data))
    diff = diff_schemas(old, new)

    if not diff.changes:
        print(f"No schema drift for '{args.name}'.")
        return 0

    if diff.breaking:
        print(f"BREAKING changes in '{args.name}':")
        for c in diff.breaking:
            print(f"  ✗ [{c.kind}] {c.column}: {c.detail}")
    if diff.safe:
        print(f"Safe changes in '{args.name}':")
        for c in diff.safe:
            print(f"  ✓ [{c.kind}] {c.column}: {c.detail}")

    if args.update and not diff.has_breaking:
        snap_path.write_text(json.dumps(new, indent=2), encoding="utf-8")
        print("Snapshot updated (safe changes only).")

    return 1 if diff.has_breaking else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="schema-drift",
        description="Snapshot dataset schemas and detect breaking changes over time.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_snap = sub.add_parser("snapshot", help="Save the current schema of a dataset.")
    p_snap.add_argument("data", help="Path to data file (.json, .jsonl, or .csv).")
    p_snap.add_argument("--name", required=True, help="Logical name for this dataset.")
    p_snap.set_defaults(func=cmd_snapshot)

    p_check = sub.add_parser("check", help="Diff new data against the saved snapshot.")
    p_check.add_argument("data", help="Path to new data file.")
    p_check.add_argument("--name", required=True, help="Logical name to compare against.")
    p_check.add_argument("--update", action="store_true",
                         help="Update the snapshot if only safe changes are found.")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

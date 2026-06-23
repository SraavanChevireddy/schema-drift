"""Core schema inference and diffing.

A "schema" here is a simple mapping of column name -> type string. We infer it
from sample data (JSON records or CSV), snapshot it to disk, and later diff a
new schema against the snapshot to classify each change as breaking or safe.

The diff logic is the valuable part and is kept pure for easy testing.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field

# Type lattice for widening: an int can safely become a float/number, anything
# can become a string. A change in the OTHER direction is "narrowing" and is a
# breaking change for most consumers.
_WIDENS_TO = {
    "null": {"bool", "int", "float", "string"},
    "bool": {"int", "float", "string"},
    "int": {"float", "string"},
    "float": {"string"},
    "string": set(),
}


def _type_of(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "string"


def _merge_type(a: str, b: str) -> str:
    """Combine two observed types into the narrowest type covering both."""
    if a == b:
        return a
    if a == "null":
        return b
    if b == "null":
        return a
    # numeric promotion
    if {a, b} == {"int", "float"}:
        return "float"
    if {a, b} <= {"bool", "int", "float"}:
        return "float" if "float" in {a, b} else "int"
    return "string"


def infer_schema_from_records(records: list[dict]) -> dict[str, str]:
    """Infer a {column: type} schema from a list of JSON-like records."""
    schema: dict[str, str] = {}
    for rec in records:
        for key, value in rec.items():
            t = _type_of(value)
            schema[key] = _merge_type(schema[key], t) if key in schema else t
    return dict(sorted(schema.items()))


def infer_schema_from_json(text: str) -> dict[str, str]:
    """Infer from a JSON array of objects, or newline-delimited JSON (JSONL)."""
    text = text.strip()
    if not text:
        return {}
    if text.startswith("["):
        records = json.loads(text)
    else:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    return infer_schema_from_records(records)


def infer_schema_from_csv(text: str) -> dict[str, str]:
    """Infer from CSV text, sniffing int/float/bool/string per column."""
    reader = csv.DictReader(io.StringIO(text))
    records: list[dict] = []
    for row in reader:
        typed = {}
        for k, v in row.items():
            typed[k] = _coerce_scalar(v)
        records.append(typed)
    return infer_schema_from_records(records)


def _coerce_scalar(v: str):
    if v is None or v == "":
        return None
    low = v.strip().lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


# ---------------------------------------------------------------------------
# Diffing
# ---------------------------------------------------------------------------

@dataclass
class Change:
    kind: str          # added | removed | type_widened | type_narrowed | type_changed
    column: str
    detail: str
    breaking: bool


@dataclass
class Diff:
    changes: list[Change] = field(default_factory=list)

    @property
    def breaking(self) -> list[Change]:
        return [c for c in self.changes if c.breaking]

    @property
    def safe(self) -> list[Change]:
        return [c for c in self.changes if not c.breaking]

    @property
    def has_breaking(self) -> bool:
        return any(c.breaking for c in self.changes)


def diff_schemas(old: dict[str, str], new: dict[str, str]) -> Diff:
    """Compare two schemas and classify each change.

    Breaking changes (will likely break downstream consumers):
      - a column was removed
      - a column's type narrowed (e.g. string -> int) or changed incompatibly
    Safe changes:
      - a new column was added
      - a column's type widened (e.g. int -> float, int -> string)
    """
    diff = Diff()

    for col in new:
        if col not in old:
            diff.changes.append(Change("added", col, f"new column ({new[col]})", breaking=False))

    for col in old:
        if col not in new:
            diff.changes.append(Change("removed", col, f"column dropped (was {old[col]})", breaking=True))
            continue
        old_t, new_t = old[col], new[col]
        if old_t == new_t:
            continue
        if new_t in _WIDENS_TO.get(old_t, set()):
            diff.changes.append(Change(
                "type_widened", col, f"{old_t} -> {new_t} (widening)", breaking=False))
        elif old_t in _WIDENS_TO.get(new_t, set()):
            diff.changes.append(Change(
                "type_narrowed", col, f"{old_t} -> {new_t} (narrowing)", breaking=True))
        else:
            diff.changes.append(Change(
                "type_changed", col, f"{old_t} -> {new_t} (incompatible)", breaking=True))

    diff.changes.sort(key=lambda c: (not c.breaking, c.column))
    return diff

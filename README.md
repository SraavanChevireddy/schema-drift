# schema-drift

> Data contracts for teams who don't have a catalog. Snapshot a dataset's schema, then **fail your CI when a breaking change sneaks in** — a dropped column, a narrowed type, an incompatible swap. Works on JSON, JSONL, and CSV today.

[![CI](https://github.com/SraavanChevireddy/schema-drift/actions/workflows/ci.yml/badge.svg)](https://github.com/SraavanChevireddy/schema-drift/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)

A producer renames a column or changes a type, and three teams downstream break at 2am. The data was "valid" — it just wasn't the *shape* anyone agreed on. **schema-drift** turns that implicit agreement into an enforced contract: snapshot the schema you expect, and check every new batch against it.

## What counts as breaking?

It classifies each change using a type-widening lattice, so you only get paged for things that actually break consumers:

| Change | Verdict | Why |
|--------|---------|-----|
| New column added | ✅ safe | Existing consumers ignore it. |
| Type widened (`int → float`, `int → string`) | ✅ safe | Old readers still parse it. |
| Column removed | ❌ breaking | Consumers referencing it fail. |
| Type narrowed (`string → int`) | ❌ breaking | Existing values may no longer fit. |
| Incompatible type change | ❌ breaking | Parsing breaks. |

## Install

```bash
pip install schema-drift        # from PyPI (once published)
# or from source:
git clone https://github.com/SraavanChevireddy/schema-drift.git
cd schema-drift && pip install -e .
```

## Usage

```bash
# 1. Snapshot the schema you expect
schema-drift snapshot orders_v1.json --name orders
# -> Snapshot saved: .schema-drift/orders.schema.json (4 columns)

# 2. Later, check new data against it
schema-drift check orders_v2.json --name orders
```

### Safe change — exits 0

```bash
$ schema-drift check examples/orders_v2_safe.json --name orders
Safe changes in 'orders':
  ✓ [added] coupon: new column (string)
```

### Breaking change — exits 1 (fails CI)

```bash
$ schema-drift check examples/orders_v3_breaking.json --name orders
BREAKING changes in 'orders':
  ✗ [removed] status: column dropped (was string)
Safe changes in 'orders':
  ✓ [type_widened] total: float -> string (widening)
```

Use `--update` on `check` to auto-advance the snapshot when only safe changes are present.

## Use it in CI

Commit the `.schema-drift/` snapshot to your repo, then gate your data pipeline:

```yaml
- run: pip install schema-drift
- run: schema-drift check latest_export.json --name orders
# non-zero exit on a breaking change fails the build
```

## How it works

1. Infer a `{column: type}` schema from sample records (JSON/JSONL/CSV), promoting types as it sees more rows (`int` + `float` → `float`, anything + `null` stays nullable).
2. Persist it as a small JSON snapshot.
3. Diff a new schema against the snapshot and classify each change via the widening lattice.

All the interesting logic is pure functions in [`schemadrift/core.py`](schemadrift/core.py) — easy to test and extend.

## Roadmap / contributing

High-value PRs: Parquet/Avro support, JDBC table introspection, nested/struct field diffing, a `--json` report for dashboards. Keep the core dependency-free; put format adapters behind optional extras.

## License

[MIT](LICENSE) © Sraavan Chevireddy

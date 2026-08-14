# Agent instructions for validate-pyproject-schema-store

## What this repo is

A plugin package that distributes a pinned, versioned snapshot of
[SchemaStore](https://www.schemastore.org) schemas for
[`validate-pyproject`](https://github.com/abravalheri/validate-pyproject). It is
not a general library; the "code" is mostly downloaded JSON schemas plus a thin
Python wrapper (`schema.py`) that exposes them as `validate-pyproject` entry
points.

## Commands

| Task                          | Command                                    |
| ----------------------------- | ------------------------------------------ |
| Run all tests (with coverage) | `hatch test -ca`                           |
| Run a single test file        | `hatch test tests/test_package.py`         |
| Lint / format / typecheck     | `hatch run lint:lint` (runs pre-commit)    |
| Pylint only                   | `hatch run pylint:lint`                    |
| Sync schemas from SchemaStore | `uv run tools/sync.py`                     |

Build backend is `hatchling`; `hatch` is the task runner (default env installer
is `uv`). Python 3.9–3.14 are supported. CI runs `uvx hatch test -ca`.

## Generated schemas — do not hand-edit

Everything in `src/validate_pyproject_schema_store/resources/` is generated:

- `tool.json` — mapping of tool name → schema URL
- `extra.json` — mapping of nested (partial) schema name → URL
- `*.schema.json` — downloaded schema files

If schema handling needs to change, edit `tools/sync.py`, then run
`uv run tools/sync.py` to regenerate.

## Schema sync (`tools/sync.py`)

The primary maintenance script — a PEP 723 self-contained uv script (needs
Python ≥3.11). It:

1. Fetches `https://json.schemastore.org/pyproject.json` and downloads each
   tool schema, plus any nested `schemastore.org` refs, into `resources/`
2. Resolves relative `$ref`s to absolute URLs and replaces `"uint64"` with
   `"uint"` (workaround for `validate-pyproject`)
3. Handles aliases (multiple tool names → same URL): each URL is downloaded
   once, stored under a URL-derived filename when needed, and only the first
   alphabetical tool name gets an entry point
4. If anything changed, updates `pyproject.toml`: `project.version` → today's
   date (`YYYY.MM.DD`) and regenerates the
   `validate_pyproject.tool_schema` entry points, excluding `setuptools` and
   `distutils`

Never bump the version manually; `sync.py` does it.

## Entry points

Defined in `pyproject.toml`:

- `[project.entry-points."validate_pyproject.tool_schema"]` — one per tool,
  all pointing at `schema:get_schema`
- `[project.entry-points."validate_pyproject.multi_schema"]` — single entry,
  `schema:get_multi_schema`
- `[project.entry-points."pipx.run"]` — makes
  `pipx run validate-pyproject-schema-store[all]` work

## Architecture notes

- `schema.py` loads JSON from `resources/` via `importlib.resources`, with LRU
  caching. `get_schema(tool)` returns one tool's schema; `get_multi_schema()`
  returns all tools plus nested schemas.
- Nested schemas (`https://json.schemastore.org/partial-*` refs) are **not
  supported** by the single-schema entry point — they are replaced with
  `"type": "object"`. The multi-schema entry point (validate-pyproject 0.24+)
  supports them properly.
- Schema filenames may be tool-named or URL-named (for aliases);
  `_tool_schema_filename` resolves which one to load.

## Testing quirks

- `tests/test_validate_pyproject.py` imports `validate_pyproject` and tests
  real validation behavior against the bundled schemas.
- `tests/conftest.py` reports installed package versions in the pytest header.

## Release flow (automated)

1. A daily cron runs `.github/workflows/bump.yml`, which runs
   `uv run tools/sync.py`
2. If schemas changed, `pyproject-schema-store-bot[bot]` opens a PR, which
   auto-merges if it only contains bot commits
3. On merge, `auto-release.yml` tags the version from `pyproject.toml` and
   creates a GitHub release; `cd.yml` then publishes to PyPI

## Conventions

- `from __future__ import annotations` is required in all Python files
  (enforced by ruff's isort rules).
- Ruff (full `ALL` ruleset) handles linting and formatting; Prettier covers
  everything else but excludes `resources/*.json`.
- Mypy is strict; `disallow_untyped_defs` applies only to
  `validate_pyproject_schema_store.*`.

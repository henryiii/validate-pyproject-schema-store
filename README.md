# validate-pyproject-schema-store

[![Actions Status][actions-badge]][actions-link]

[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

<!-- SPHINX-START -->

This provides a versioned copy of [SchemaStore][] for [validate-pyproject][].
You can pin this to get a stable set of schema files.

Nested schemas are not supported yet. Support will require updates to
validate-pyproject. For now, they are replaced with `"type": "object"`.

## Usage

The following should be supported:

### Installing alongside validate-pyproject

Just use `pip install validate-pyproject-schema-store` wherever you have
`validate-pyproject[all]` installed. You can "inject" it if using pipx, or use
`--pip-args` if using `pipx run`.

In pre-commit, this would be:

```yaml
repos:
  - repo: https://github.com/abravalheri/validate-pyproject
    rev: <insert here>
    hooks:
      - id: validate-pyproject
        additional_dependencies: [validate-pyproject[all], validate-pyproject-schema-store]
```

### Direct usage

For pre-commit or pipx, you can simplify this a bit by using this package
directly. That looks like this:

```bash
pipx run validate-pyproject-schema-store[all]
```

Or for pre-commit:

```yaml
repos:
  - repo: https://github.com/henryiii/validate-pyproject-schema-store
    rev: <insert here>
    hooks:
      - id: validate-pyproject
```

This also has the benefit that the version will be pinned and updated by
pre-commit automatically.

## Developing

This project uses `hatch>=1.10`. You can run the sync script by running:

```bash
hatch run tools/sync.py
```

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/henryiii/validate-pyproject-schema-store/workflows/CI/badge.svg
[actions-link]:             https://github.com/henryiii/validate-pyproject-schema-store/actions
[pypi-link]:                https://pypi.org/project/validate-pyproject-schema-store/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/validate-pyproject-schema-store
[pypi-version]:             https://img.shields.io/pypi/v/validate-pyproject-schema-store
[validate-pyproject]:       https://github.com/abravalheri/validate-pyproject
[schemastore]:              https://www.schemastore.org
<!-- prettier-ignore-end -->

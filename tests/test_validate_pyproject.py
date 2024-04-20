from __future__ import annotations

import sys

from validate_pyproject import api

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


def test_vpp_loads(caplog):
    pyproject_as_dict = tomllib.loads("""
        [tool.ruff]
        src = ["src"]
    """)

    validator = api.Validator()
    validator(pyproject_as_dict)
    assert (
        "validate_pyproject_schema_store.schema.get_schema defines `tool.poetry` schema"
        in caplog.text
    )


def test__loads(caplog):
    pyproject_as_dict = tomllib.loads("""
        [tool.hatch.env]
        requires = [
            "hatch-pip-compile"
        ]
    """)

    validator = api.Validator()
    validator(pyproject_as_dict)
    assert (
        "validate_pyproject_schema_store.schema.get_schema defines `tool.hatch` schema"
        in caplog.text
    )

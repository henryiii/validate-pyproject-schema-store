from __future__ import annotations

import sys

import pytest
from validate_pyproject import api
from validate_pyproject.error_reporting import ValidationError

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
        "validate_pyproject_schema_store.schema.get_multi_schema:poetry defines `tool.poetry` schema"
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
        "validate_pyproject_schema_store.schema.get_multi_schema:hatch defines `tool.hatch` schema"
        in caplog.text
    )


def test_version_24_multi():
    pyproject_as_dict = tomllib.loads("""
        [tool.pdm]
        dockerize.anything = "invalid"
    """)

    validator = api.Validator()
    with pytest.raises(ValidationError, match="must not contain"):
        validator(pyproject_as_dict)

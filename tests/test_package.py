from __future__ import annotations

import pytest

from validate_pyproject_schema_store.schema import get_schema


def test_get_unknown_schema():
    with pytest.raises(AssertionError):
        get_schema("unknown")


@pytest.mark.parametrize(
    "tool", ["poetry", "cibuildwheel", "mypy", "pdm", "scikit-build", "setuptools"]
)
def test_get_schema_partials(tool: str):
    schema = get_schema(tool)
    assert schema["$id"] == f"https://json.schemastore.org/partial-{tool}.json"
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert "properties" in schema


@pytest.mark.parametrize("tool", ["hatch", "ruff"])
def test_get_schema_full(tool: str):
    schema = get_schema(tool)
    assert schema["$id"] == f"https://json.schemastore.org/{tool}.json"
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert "properties" in schema

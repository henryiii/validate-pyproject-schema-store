from __future__ import annotations

import pytest

from validate_pyproject_schema_store.schema import get_schema


def test_get_unknown_schema():
    with pytest.raises(AssertionError):
        get_schema("unknown")


def test_get_schema_unscoped():
    tool = "poetry"
    schema = get_schema(tool)
    assert schema["$id"] == f"https://json.schemastore.org/{tool}.json"
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert "properties" in schema


def test_get_schema_scoped():
    tool = "cibuildwheel"
    schema = get_schema(tool)
    assert schema["$id"] == f"https://json.schemastore.org/{tool}.json"
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert "properties" in schema

from __future__ import annotations

import pytest

from validate_pyproject_schema_store.schema import get_multi_schema, get_schema


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


def test_no_nested_schema():
    schema = get_schema("pdm")
    properties = schema["properties"]
    for prop in properties.values():
        assert not prop.get("$ref", "")


def test_multi_schema():
    multi_schema = get_multi_schema()
    assert (
        multi_schema["tools"]["ruff"]["$id"] == "https://json.schemastore.org/ruff.json"
    )
    assert (
        multi_schema["tools"]["ruff"]["$schema"]
        == "http://json-schema.org/draft-07/schema#"
    )

    assert (
        multi_schema["tools"]["pdm"]["properties"]["dockerize"]["$ref"]
        == "https://json.schemastore.org/partial-pdm-dockerize.json"
    )
    (pdm_docker,) = [
        s
        for s in multi_schema["schemas"]
        if s["$id"] == "https://json.schemastore.org/partial-pdm-dockerize.json"
    ]
    assert pdm_docker["$schema"] == "http://json-schema.org/draft-07/schema#"

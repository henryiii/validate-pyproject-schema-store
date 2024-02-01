from __future__ import annotations

from validate_pyproject import api


def test_vpp_loads(caplog):
    pyproject_as_dict = {
        "tool": {
            "ruff": {
                "src": ["src"],
            }
        }
    }
    validator = api.Validator()
    validator(pyproject_as_dict)
    assert (
        "validate_pyproject_schema_store.schema.get_schema defines `tool.poetry` schema"
        in caplog.text
    )

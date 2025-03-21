from __future__ import annotations

import functools
import json
import sys
from pathlib import Path
from typing import Any

if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files


DIR = Path(__file__).parent.resolve()
RESOURCES = files("validate_pyproject_schema_store") / "resources"


__all__ = ["get_schema"]


def __dir__() -> list[str]:
    return __all__


@functools.lru_cache
def get_tools() -> dict[str, str]:
    tool_file = RESOURCES / "tool.json"
    with tool_file.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


@functools.lru_cache
def get_extra() -> dict[str, str]:
    extra_file = RESOURCES / "extra.json"
    with extra_file.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _load_schema(filename: str) -> dict[str, Any]:
    tool_file = RESOURCES / filename
    with tool_file.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def get_schema(tool: str) -> dict[str, Any]:
    tools = get_tools()
    if tool not in tools:
        msg = f"Must be valid tool, got {tool}"
        raise AssertionError(msg)

    tool_json = _load_schema(f"{tool}.schema.json")
    orig_tool_json = tool_json.copy()

    _, _, path = tools[tool].partition("#")
    for item in path.split("/"):
        if item:
            tool_json = tool_json[item]
    tool_json["$id"] = orig_tool_json["$id"]
    tool_json["$schema"] = orig_tool_json["$schema"]
    if "definitions" in orig_tool_json:
        tool_json["definitions"] = orig_tool_json["definitions"]

    # Nested schemas are not supported with this entry point, only with the multi entry point (validate-pyproject 0.24+)
    properties = tool_json.get("properties", {})
    for prop in properties.values():
        if prop.get("$ref", "").startswith("https://json.schemastore.org/partial"):
            prop.clear()
            prop["type"] = "object"

    return tool_json


get_schema.priority = -2  # type: ignore[attr-defined]


def get_multi_schema() -> dict[str, Any]:
    tools = get_tools()
    extras = get_extra()

    return {
        "tools": {tool: _load_schema(f"{tool}.schema.json") for tool in tools},
        "schemas": [_load_schema(f"{extra}.schema.json") for extra in extras],
        "priority": -1,
    }

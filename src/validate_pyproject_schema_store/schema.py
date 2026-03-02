from __future__ import annotations

import functools
import json
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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


def _schema_name_from_url(url: str) -> str:
    parsed = urlparse(url.partition("#")[0])
    return Path(parsed.path).name.removesuffix(".json")


def _tool_schema_filename(tool: str, url: str) -> str:
    by_url = f"{_schema_name_from_url(url)}.schema.json"
    by_url_path = RESOURCES / by_url
    if by_url_path.is_file():
        return by_url
    return f"{tool}.schema.json"


def get_schema(tool: str) -> dict[str, Any]:
    tools = get_tools()
    if tool not in tools:
        msg = f"Must be valid tool, got {tool}"
        raise AssertionError(msg)

    tool_json = _load_schema(_tool_schema_filename(tool, tools[tool]))
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
        "tools": {
            tool: _load_schema(_tool_schema_filename(tool, url))
            for tool, url in tools.items()
        },
        "schemas": [
            _load_schema(f"{_schema_name_from_url(url)}.schema.json")
            for url in extras.values()
        ],
        "priority": -1,
    }

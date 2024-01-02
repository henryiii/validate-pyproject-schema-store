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


def get_schema(tool: str) -> dict[str, Any]:
    tools = get_tools()
    if tool not in tools:
        msg = f"Must be valid tool, got {tool}"
        raise AssertionError(msg)

    tool_file = RESOURCES / f"{tool}.schema.json"
    with tool_file.open(encoding="utf-8") as f:
        tool_json = json.load(f)

    orig_tool_json = tool_json.copy()

    _, _, path = tools[tool].partition("#")
    for item in path.split("/"):
        if item:
            tool_json = tool_json[item]
    tool_json["$id"] = orig_tool_json["$id"]
    tool_json["$schema"] = orig_tool_json["$schema"]
    if "definitions" in orig_tool_json:
        tool_json["definitions"] = orig_tool_json["definitions"]
    return tool_json  # type: ignore[no-any-return]

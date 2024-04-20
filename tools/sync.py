#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [ "aiohttp", "tomlkit" ]
# ///


from __future__ import annotations

import asyncio
import datetime
import json
from pathlib import Path
from typing import Any

import aiohttp
import tomlkit

DIR = Path(__file__).parent.resolve()
RESOURCES = DIR.parent / "src/validate_pyproject_schema_store/resources"
RESOURCES.mkdir(parents=True, exist_ok=True)


async def get_url(session, url: str) -> dict[str, Any]:
    print("Getting", url)
    async with session.get(url) as resp:
        return await resp.json()  # type: ignore[no-any-return]


def write_if_changed(filename: Path, contents: str) -> bool:
    prev = filename.read_text(encoding="utf-8") if filename.is_file() else ""
    if prev == contents:
        return False
    filename.write_text(contents, encoding="utf-8")
    return True


async def main() -> None:
    changed = False

    async with aiohttp.ClientSession() as session:
        res_json = await get_url(session, "https://json.schemastore.org/pyproject.json")

        tool_properties = res_json["properties"]["tool"]["properties"]
        tool_table = {t: d["$ref"] for t, d in tool_properties.items() if "$ref" in d}

        tool_json = RESOURCES / "tool.json"
        new = json.dumps(tool_table, indent=2) + "\n"
        changed |= write_if_changed(tool_json, new)

        async with asyncio.TaskGroup() as tg:
            results = {
                tool: tg.create_task(get_url(session, ref.partition("#")[0]))
                for tool, ref in tool_table.items()
            }

        for tool, future in results.items():
            target = RESOURCES / f"{tool}.schema.json"
            result = future.result()

            new = json.dumps(result, indent=2) + "\n"
            changed |= write_if_changed(target, new)

        if changed:
            pyproject = DIR.parent / "pyproject.toml"
            doc = tomlkit.parse(pyproject.read_text())
            table = tomlkit.table()
            for tool in tool_table:
                if tool not in {"setuptools", "distutils"}:
                    table.add(tool, "validate_pyproject_schema_store.schema:get_schema")
            doc["project"]["entry-points"]["validate_pyproject.tool_schema"] = table  # type: ignore[index]
            doc["project"]["version"] = f"{datetime.date.today():%Y.%m.%d}"  # type: ignore[index]
            pyproject.write_text(tomlkit.dumps(doc))


asyncio.run(main())

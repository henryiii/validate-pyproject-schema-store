# /// pyproject
# run.dependencies = [ "aiohttp", "tomlkit" ]
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
        return await resp.json()


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        res_json = await get_url(session, "https://json.schemastore.org/pyproject.json")

        tool_properties = res_json["properties"]["tool"]["properties"]
        tool_table = {t: d["$ref"] for t, d in tool_properties.items() if "$ref" in d}

        pyproject = DIR.parent / "pyproject.toml"
        doc = tomlkit.parse(pyproject.read_text())
        table = tomlkit.table()
        for tool in tool_table:
            if tool not in {"setuptools", "distutils"}:
                table.add(tool, "validate_pyproject_schema_store.schema:get_schema")
        doc["project"]["entry-points"]["validate_pyproject.tool_schema"] = table
        doc["project"]["version"] = f"{datetime.date.today():%Y.%m.%d}"
        pyproject.write_text(tomlkit.dumps(doc))

        with RESOURCES.joinpath("tool.json").open("wt", encoding="utf-8") as f:
            json.dump(tool_table, f, indent=2)
            f.write("\n")

        async with asyncio.TaskGroup() as tg:
            results = {
                tool: tg.create_task(get_url(session, ref.partition("#")[0]))
                for tool, ref in tool_table.items()
            }

        for tool, result in results.items():
            target = RESOURCES / f"{tool}.schema.json"
            with target.open("wt", encoding="utf-8") as f:
                json.dump(result.result(), f, indent=2)
                f.write("\n")


asyncio.run(main())

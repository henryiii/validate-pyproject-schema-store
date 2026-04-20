#!/usr/bin/env -S uv run
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
from urllib.parse import urlparse

import aiohttp
import tomlkit

DIR = Path(__file__).parent.resolve()
RESOURCES = DIR.parent / "src/validate_pyproject_schema_store/resources"
RESOURCES.mkdir(parents=True, exist_ok=True)


async def get_url(session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
    print("Getting", url)
    async with session.get(url) as resp:
        return await resp.json()  # type: ignore[no-any-return]


def schema_name_from_url(url: str) -> str:
    parsed = urlparse(url.partition("#")[0])
    return Path(parsed.path).name.removesuffix(".json")


def iter_schema_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            refs.add(ref)
        for nested in value.values():
            refs.update(iter_schema_refs(nested))
    elif isinstance(value, list):
        for nested in value:
            refs.update(iter_schema_refs(nested))
    return refs


def write_if_changed(filename: Path, contents: dict[str, Any]) -> bool:
    new = json.dumps(contents, indent=2) + "\n"
    new = new.replace(
        '"uint64"', '"uint"'
    )  # Workaround for validate-pyproject missing this
    prev = filename.read_text(encoding="utf-8") if filename.is_file() else ""
    if prev == new:
        return False
    filename.write_text(new, encoding="utf-8")
    return True


async def get_tool(
    session: aiohttp.ClientSession, tools: dict[str, Any]
) -> dict[str, Any]:
    try:
        return tools["properties"]  # type: ignore[no-any-return]
    except KeyError:
        url = tools["$ref"]
        res = await get_url(session, url)
        return res["properties"]  # type: ignore[no-any-return]


async def main() -> None:
    changed = False

    async with aiohttp.ClientSession() as session:
        res_json = await get_url(session, "https://json.schemastore.org/pyproject.json")

        tool_properties = await get_tool(session, res_json["properties"]["tool"])
        tool_table = {t: d["$ref"] for t, d in tool_properties.items() if "$ref" in d}

        tool_json = RESOURCES / "tool.json"
        changed |= write_if_changed(tool_json, tool_table)
        nested = {}

        # Track which URLs we've already downloaded to handle aliases (multiple tools -> same URL)
        url_to_filename: dict[str, str] = {}

        async with asyncio.TaskGroup() as tg:
            results = {
                tool: tg.create_task(get_url(session, ref.partition("#")[0]))
                for tool, ref in tool_table.items()
            }

        for tool, future in results.items():
            ref = tool_table[tool]
            result = future.result()

            nested_names = {
                schema_name_from_url(url)
                for url in iter_schema_refs(result)
                if url.startswith(
                    (
                        "https://json.schemastore.org/",
                        "https://www.schemastore.org/",
                    )
                )
            }
            ref_name = schema_name_from_url(ref)

            # Check if we've already downloaded this URL (alias handling)
            canonical_url = ref.partition("#")[0]
            if canonical_url in url_to_filename:
                # This is an alias, filename was already determined
                target_name = url_to_filename[canonical_url]
            else:
                # Determine filename: prefer URL-based name if tool name differs (for aliases)
                target_name = (
                    ref_name if tool in nested_names and ref_name != tool else tool
                )
                url_to_filename[canonical_url] = target_name

            target = RESOURCES / f"{target_name}.schema.json"

            for url in iter_schema_refs(result):
                if url.startswith(
                    (
                        "https://json.schemastore.org/",
                        "https://www.schemastore.org/",
                    )
                ):
                    if url.partition("#")[0] == canonical_url:
                        continue
                    filename = schema_name_from_url(url)
                    nested_target = RESOURCES / f"{filename}.schema.json"
                    nested_result = await get_url(session, url)
                    changed |= write_if_changed(nested_target, nested_result)
                    nested[filename] = url

            changed |= write_if_changed(target, result)

        extra_json = RESOURCES / "extra.json"
        changed |= write_if_changed(extra_json, nested)

        if changed:
            pyproject = DIR.parent / "pyproject.toml"
            doc = tomlkit.parse(pyproject.read_text())

            # De-duplicate aliases (multiple tools -> same URL) for entry points
            # Only register the canonical tool (first in alphabetical order) for each URL
            url_to_tools: dict[str, list[str]] = {}
            for tool, ref in tool_table.items():
                canonical_url = ref.partition("#")[0]
                if canonical_url not in url_to_tools:
                    url_to_tools[canonical_url] = []
                url_to_tools[canonical_url].append(tool)

            canonical_tools = {sorted(tools)[0] for tools in url_to_tools.values()}

            table = tomlkit.table()
            for tool in tool_table:
                if tool not in {"setuptools", "distutils"} and tool in canonical_tools:
                    table.add(tool, "validate_pyproject_schema_store.schema:get_schema")
            doc["project"]["entry-points"]["validate_pyproject.tool_schema"] = table  # type: ignore[index]
            doc["project"]["version"] = f"{datetime.date.today():%Y.%m.%d}"  # type: ignore[index]
            pyproject.write_text(tomlkit.dumps(doc))


asyncio.run(main())

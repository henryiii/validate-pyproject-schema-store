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
from urllib.parse import urljoin, urlparse

import aiohttp
import tomlkit

DIR = Path(__file__).parent.resolve()
RESOURCES = DIR.parent / "src/validate_pyproject_schema_store/resources"
RESOURCES.mkdir(parents=True, exist_ok=True)

PYPROJECT_URL = "https://json.schemastore.org/pyproject.json"


def resolve_ref(ref: str, base: str) -> str:
    """Resolve a potentially relative $ref against a base URL."""
    if ref.startswith(("http://", "https://", "#")):
        return ref
    return urljoin(base, ref)


def resolve_schema_refs(obj: Any, base_url: str) -> Any:
    """Recursively resolve all relative $ref URLs in a schema object to absolute URLs."""
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str):
                new[k] = resolve_ref(v, base_url)
            else:
                new[k] = resolve_schema_refs(v, base_url)
        return new
    if isinstance(obj, list):
        return [resolve_schema_refs(item, base_url) for item in obj]
    return obj


async def get_url(
    session: aiohttp.ClientSession,
    url: str,
    resolve_refs: bool = False,
    base_url: str = "",
) -> dict[str, Any]:
    print("Getting", url)
    async with session.get(url) as resp:
        data = await resp.json()
        if resolve_refs:
            data = resolve_schema_refs(data, base_url or url)
        return data  # type: ignore[no-any-return]


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
        tool_table = {
            t: resolve_ref(d["$ref"], PYPROJECT_URL)
            for t, d in tool_properties.items()
            if "$ref" in d
        }

        tool_json = RESOURCES / "tool.json"
        changed |= write_if_changed(tool_json, tool_table)
        nested = {}

        # Track which URLs we've already downloaded to handle aliases
        url_to_filename: dict[str, str] = {}

        async with asyncio.TaskGroup() as tg:
            results = {
                tool: tg.create_task(
                    get_url(
                        session,
                        ref.partition("#")[0],
                        resolve_refs=True,
                        base_url=PYPROJECT_URL,
                    )
                )
                for tool, ref in tool_table.items()
            }

        for tool, future in results.items():
            ref = tool_table[tool]
            result = future.result()
            base_url = ref.partition("#")[0]

            nested_names = {
                schema_name_from_url(url)
                for raw_url in iter_schema_refs(result)
                for url in [resolve_ref(raw_url, base_url)]
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
                # Determine filename: prefer URL-based name when the file already
                # exists (e.g. previously created as a nested schema) or when the
                # tool name appears in the schema's own nested refs.
                url_named_path = RESOURCES / f"{ref_name}.schema.json"
                target_name = (
                    ref_name
                    if ref_name != tool
                    and (url_named_path.is_file() or tool in nested_names)
                    else tool
                )
                url_to_filename[canonical_url] = target_name

            target = RESOURCES / f"{target_name}.schema.json"

            for raw_url in iter_schema_refs(result):
                url = resolve_ref(raw_url, base_url)
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
                    nested_result = await get_url(
                        session, url, resolve_refs=True, base_url=PYPROJECT_URL
                    )
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

from __future__ import annotations

import contextlib
import sys
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

DIR = Path(__file__).parent.resolve()
BASE = DIR.parent


def pytest_report_header() -> str:
    with BASE.joinpath("pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)
    project = pyproject.get("project", {})

    pkgs = project.get("dependencies", [])
    pkgs += [p for ps in project.get("optional-dependencies", {}).values() for p in ps]
    pkgs += pyproject.get("dependency-groups", {}).get("test", [])
    pkgs.append(project["name"])

    interesting_packages = {Requirement(p).name for p in pkgs}

    valid = []
    for package in sorted(interesting_packages):
        with contextlib.suppress(ModuleNotFoundError):
            valid.append(f"{package}=={metadata.version(package)}")
    reqs = " ".join(valid)
    lines = [
        f"installed packages of interest: {reqs}",
    ]
    return "\n".join(lines)

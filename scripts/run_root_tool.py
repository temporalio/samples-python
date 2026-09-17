"""Run a root quality tool while excluding nested Python projects."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def find_nested_projects(root: Path) -> list[str]:
    projects: list[str] = []

    for directory, child_directories, filenames in os.walk(root):
        path = Path(directory)
        if path != root and "pyproject.toml" in filenames:
            projects.append(path.relative_to(root).as_posix())
            child_directories.clear()
            continue

        child_directories[:] = [
            child
            for child in child_directories
            if not child.startswith(".")
            and child not in {"__pycache__", "node_modules"}
        ]

    return sorted(projects)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"mypy", "ruff"}:
        print("usage: run_root_tool.py {mypy,ruff} [args ...]", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent.parent
    projects = find_nested_projects(root)
    tool, *arguments = sys.argv[1:]

    if tool == "ruff":
        command = [
            tool,
            *arguments,
            "--config",
            f"extend-exclude={json.dumps(projects)}",
        ]
    else:
        command = [tool, *arguments]
        project_pattern = "|".join(re.escape(project) for project in projects)
        if project_pattern:
            command.extend(["--exclude", rf"^(?:\./)?(?:{project_pattern})(?:/|$)"])

    return subprocess.run(command, cwd=root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

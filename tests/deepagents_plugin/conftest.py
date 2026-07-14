"""Collection guard for the Deep Agents plugin tests.

The `temporalio-contrib-deepagents` plugin (and its `deepagents` /
`langchain` runtime deps) require Python >= 3.11. It is also experimental and
not yet published to PyPI, so it is deliberately kept out of every dependency
group — the canonical `poe test` run (`uv run --all-groups pytest`) never
installs it. These test modules import `temporalio.contrib.deepagents` at module
load, which would raise `ImportError` during collection whenever the plugin is
absent (any interpreter) or the interpreter is < 3.11 — failing the whole
session.

A module-level `pytest.mark.skipif` cannot help here: the mark is only read
*after* the module is imported, so the import error fires first. `collect_ignore`
is evaluated before any test module is imported, so it skips these files
cleanly when the plugin is unavailable while still running them once it is
installed on 3.11+.
"""

import importlib.util
import sys

collect_ignore_glob: list[str] = []

if sys.version_info < (3, 11) or (
    importlib.util.find_spec("temporalio.contrib.deepagents") is None
):
    collect_ignore_glob = ["*_test.py"]

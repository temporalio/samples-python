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

The guard performs a real (guarded) import rather than `find_spec`: the
subpackage can exist on disk while its runtime deps do not — e.g. a
plugin-carrying `temporalio` build installed without the `deepagents`
dependency group — and only an actual import proves the test modules can load.
The version check runs first so the import is never attempted on interpreters
the plugin does not support.
"""

import sys

collect_ignore_glob: list[str] = []

_plugin_available = False
if sys.version_info >= (3, 11):
    try:
        import temporalio.contrib.deepagents  # noqa: F401

        _plugin_available = True
    except ImportError:
        _plugin_available = False

if not _plugin_available:
    collect_ignore_glob = ["*_test.py"]

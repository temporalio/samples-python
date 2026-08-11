"""Collection guard for the Deep Agents plugin tests.

The plugin ships as the `temporalio[deepagents]` extra and requires
Python >= 3.11. It is merged to sdk-python main but the current PyPI
release (1.31.0) predates the merge, so the `deepagents` dependency group
cannot install it yet and the canonical `poe test` run
(`uv run --all-groups pytest`) does not have it. These test modules import
`temporalio.contrib.deepagents` at module load, which would raise
`ImportError` during collection whenever the plugin is absent (any
interpreter) or the interpreter is < 3.11 — failing the whole session.

A module-level `pytest.mark.skipif` cannot help here: the mark is only read
*after* the module is imported, so the import error fires first. `collect_ignore`
is evaluated before any test module is imported, so it skips these files
cleanly when the plugin is unavailable while still running them once it is
installed on 3.11+ (interim: from sdk-python main per the suite README;
after the release that ships the extra: via the `deepagents` group, at which
point this guard becomes a no-op and the suite runs in CI).

The guard performs a real (guarded) import rather than `find_spec`: the
subpackage can exist on disk while its runtime deps do not — e.g. a
plugin-carrying `temporalio` build installed without its extra deps — and
only an actual import proves the test modules can load. The version check
runs first so the import is never attempted on interpreters the plugin does
not support. When the guard is active, `pytest_report_header` announces it
so the non-collection is visible in CI output rather than silent.
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


def pytest_report_header(config) -> str | None:
    """Make the guard visible in the pytest header instead of silent."""
    if collect_ignore_glob:
        return (
            "deepagents_plugin: temporalio.contrib.deepagents not importable "
            "on this interpreter/environment; sample tests NOT collected "
            "(see tests/deepagents_plugin/conftest.py)"
        )
    return None

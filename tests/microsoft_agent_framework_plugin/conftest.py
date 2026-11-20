"""Collection guard for the Agent Framework plugin tests.

The plugin ships as the standalone `temporalio-microsoft-agent-framework` package, which
the `microsoft-agent-framework` dependency group installs on Python >= 3.11 only, because
the plugin declares `requires-python = ">=3.11"`, as Temporal Python SDK 1.36
does. These test modules import
`temporalio.microsoft_agent_framework` at module load, which would raise `ImportError`
during collection on 3.10 or in an environment synced without the group, and
fail the whole session.

A module-level `pytest.mark.skipif` cannot help: the mark is read after the
module is imported, so the import error fires first. `collect_ignore_glob` is
evaluated before any test module is imported, so it skips these files cleanly
when the plugin is unavailable and runs them on any 3.11+ environment synced
with the group, the canonical CI run included. The guard does a real import
rather than `find_spec`, because the package can exist on disk while its
runtime dependencies do not. When the guard is active, `pytest_report_header`
says so in the pytest header.
"""

import sys

collect_ignore_glob: list[str] = []

_plugin_available = False
if sys.version_info >= (3, 11):
    try:
        import temporalio.microsoft_agent_framework  # noqa: F401

        _plugin_available = True
    except ImportError:
        _plugin_available = False

if not _plugin_available:
    collect_ignore_glob = ["*_test.py"]


def pytest_report_header(config) -> str | None:
    """Make the guard visible in the pytest header instead of silent."""
    if collect_ignore_glob:
        return (
            "microsoft_agent_framework_plugin: temporalio.microsoft_agent_framework not importable "
            "on this interpreter/environment; sample tests NOT collected "
            "(see tests/microsoft_agent_framework_plugin/conftest.py)"
        )
    return None

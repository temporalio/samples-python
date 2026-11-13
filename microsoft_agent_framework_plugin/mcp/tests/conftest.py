"""Collection guard for the MCP sample tests.

The sample needs Python 3.11 and the plugin. On other interpreters the project's
dependencies resolve to nothing, so the test module cannot be imported; skip
its collection instead of failing the session, and do not treat the empty run
as a failure.
"""

import sys

import pytest

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


def pytest_report_header(config: pytest.Config) -> str | None:
    if collect_ignore_glob:
        return (
            "microsoft_agent_framework_plugin/mcp: temporalio.microsoft_agent_framework not importable "
            "on this interpreter/environment; sample tests NOT collected"
        )
    return None


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if collect_ignore_glob and exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK

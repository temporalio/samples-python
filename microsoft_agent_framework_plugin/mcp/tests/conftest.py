"""Collection guard for the MCP sample tests.

The plugin needs Python 3.11, so below it the project's dependencies resolve
to nothing and the test module cannot be imported: skip its collection and do
not treat the empty run as a failure. On 3.11 and later the plugin is always
installed, so an ImportError there fails the session instead of hiding.
"""

import sys

import pytest

collect_ignore_glob: list[str] = []
if sys.version_info < (3, 11):
    collect_ignore_glob = ["*_test.py"]


def pytest_report_header(config: pytest.Config) -> str | None:
    if collect_ignore_glob:
        return (
            "microsoft_agent_framework_plugin/mcp: Python below 3.11; "
            "sample tests NOT collected"
        )
    return None


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if collect_ignore_glob and exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK

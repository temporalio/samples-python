from typing import Any

import pytest
from temporalio.common import ActivitySessionOptions, UseWorkflowSession
from temporalio.worker import SingleSessionAdmission, WorkerSessionConfig
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

import workflows
from activities import execute_code
from agentcore_worker import make_plugin, session_config_for


def test_session_id_maps_to_single_session_admission() -> None:
    config = session_config_for("runtime-session-123")

    assert config == WorkerSessionConfig(
        admission=SingleSessionAdmission(stable_identity="runtime-session-123")
    )


@pytest.mark.parametrize("session_id", [None, ""])
def test_missing_session_id_falls_back_to_no_admission(
    session_id: str | None,
) -> None:
    assert session_config_for(session_id) == WorkerSessionConfig(admission=None)


class _FakeClient:
    """Stands in for the Client the Worker puts in the config; no server needed."""

    def config(self, **_kwargs: Any) -> dict[str, Any]:
        return {}


def _worker_config(**extra: Any) -> Any:
    # The shape Worker(...) hands to plugins: its own kwargs, merged before any
    # plugin (Client-registered ones included) runs configure_worker.
    return {
        "client": _FakeClient(),
        "task_queue": workflows.TASK_QUEUE,
        "workflows": [workflows.StrandsAgentWorkflow],
        "activities": [execute_code],
        "interceptors": [],
        "workflow_runner": SandboxedWorkflowRunner(),  # Worker's default
        **extra,
    }


def test_plugin_fills_workflow_session_on_activities() -> None:
    config = make_plugin().configure_worker(
        _worker_config(session_config=session_config_for("s"))
    )

    options = [
        i.options for i in config["interceptors"] if hasattr(i, "options")
    ]  # the plugin's activity-session interceptor
    assert options == [ActivitySessionOptions(placement=UseWorkflowSession())]


def test_plugin_requires_session_config() -> None:
    with pytest.raises(ValueError, match="session_config"):
        make_plugin().configure_worker(_worker_config())

"""Single-activity workflow that delegates the agentic loop to the triage activity.

Workflow ID is set deterministically by the webhook receiver
(triage-${alertname}-${service}), so re-fires from AlertManager re-attach
to the running workflow rather than spawning a new one.
"""
from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from triage_activity import triage_incident_activity
    from triage_types import AlertPayload, TriageResult


@workflow.defn(name="incidentTriageWorkflow")
class IncidentTriageWorkflow:
    def __init__(self) -> None:
        self._current_alert: AlertPayload | None = None
        self._result: TriageResult | None = None

    @workflow.run
    async def run(self, initial_alert: AlertPayload) -> TriageResult:
        self._current_alert = initial_alert
        # Single activity — matches lexicon-temporal's `agenticHitl` profile:
        # 8h start-to-close (operator may take hours), 120s heartbeat (Claude
        # turn worst case), 1 attempt (AgenticSession heartbeat is the resume).
        self._result = await workflow.execute_activity(
            triage_incident_activity,
            self._current_alert,
            start_to_close_timeout=timedelta(hours=8),
            heartbeat_timeout=timedelta(seconds=120),
        )
        return self._result

    @workflow.signal(name="alert-update")
    def alert_update(self, alert: AlertPayload) -> None:
        # Webhook may re-fire with refreshed alert state. The agent reads
        # the latest via the current-alert query.
        self._current_alert = alert

    @workflow.query(name="current-alert")
    def current_alert(self) -> AlertPayload | None:
        return self._current_alert

    @workflow.query(name="triage-result")
    def triage_result(self) -> TriageResult | None:
        return self._result

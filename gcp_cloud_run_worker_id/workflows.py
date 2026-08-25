"""Workflow used by the Cloud Run worker sample."""

from __future__ import annotations

from datetime import timedelta

from temporalio import common, workflow

with workflow.unsafe.imports_passed_through():
    from activities import compose_greeting


# PINNED matches the default versioning behavior the Cloud Run helper sets on
# the worker's deployment config: an execution stays on the build id (Cloud Run
# revision) that started it until it is explicitly migrated.
@workflow.defn(versioning_behavior=common.VersioningBehavior.PINNED)
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("GreetingWorkflow started for %s", name)
        return await workflow.execute_activity(
            compose_greeting,
            name,
            start_to_close_timeout=timedelta(seconds=10),
        )

"""Workflow definitions for the worker versioning sample."""

from datetime import timedelta

from temporalio import common, workflow

with workflow.unsafe.imports_passed_through():
    from worker_versioning.activities import (
        IncompatibleActivityInput,
        some_activity,
        some_incompatible_activity,
    )


@workflow.defn(
    name="AutoUpgrading", versioning_behavior=common.VersioningBehavior.AUTO_UPGRADE
)
class AutoUpgradingWorkflowV1:
    """AutoUpgradingWorkflowV1 will automatically move to the latest worker version. We'll be making
    changes to it, which must be replay safe.

    Note that generally you won't want or need to include a version number in your workflow name if
    you're using the worker versioning feature. This sample does it to illustrate changes to the
    same code over time - but really what we're demonstrating here is the evolution of what would
    have been one workflow definition.
    """

    def __init__(self) -> None:
        self.signals: list[str] = []

    @workflow.run
    async def run(self) -> None:
        workflow.logger.info(
            "Changing workflow v1 started.", extra={"StartTime": workflow.now()}
        )

        # This workflow will listen for signals from our starter, and upon each signal either run
        # an activity, or conclude execution.
        while True:
            await workflow.wait_condition(lambda: len(self.signals) > 0)
            signal = self.signals.pop(0)

            if signal == "do-activity":
                workflow.logger.info("Changing workflow v1 running activity")
                await workflow.execute_activity(
                    some_activity, "v1", start_to_close_timeout=timedelta(seconds=10)
                )
            else:
                workflow.logger.info("Concluding workflow v1")
                return

    @workflow.signal
    async def do_next_signal(self, signal: str) -> None:
        """Signal to perform next action."""
        self.signals.append(signal)


@workflow.defn(
    name="AutoUpgrading", versioning_behavior=common.VersioningBehavior.AUTO_UPGRADE
)
class AutoUpgradingWorkflowV1b:
    """AutoUpgradingWorkflowV1b represents us having made *compatible* changes to
    AutoUpgradingWorkflowV1.

    The compatible changes we've made are:
      - Altering the log lines
      - Using the workflow.patched API to properly introduce branching behavior while maintaining
        compatibility
    """

    def __init__(self) -> None:
        self.signals: list[str] = []

    @workflow.run
    async def run(self) -> None:
        workflow.logger.info(
            "Changing workflow v1b started.", extra={"StartTime": workflow.now()}
        )

        # This workflow will listen for signals from our starter, and upon each signal either run
        # an activity, or conclude execution.
        while True:
            await workflow.wait_condition(lambda: len(self.signals) > 0)
            signal = self.signals.pop(0)

            if signal == "do-activity":
                workflow.logger.info("Changing workflow v1b running activity")
                if workflow.patched("DifferentActivity"):
                    await workflow.execute_activity(
                        some_incompatible_activity,
                        IncompatibleActivityInput(called_by="v1b", more_data="hello!"),
                        start_to_close_timeout=timedelta(seconds=10),
                    )
                else:
                    # Note it is a valid compatible change to alter the input to an activity.
                    # However, because we're using the patched API, this branch will never be
                    # taken.
                    await workflow.execute_activity(
                        some_activity,
                        "v1b",
                        start_to_close_timeout=timedelta(seconds=10),
                    )
            else:
                workflow.logger.info("Concluding workflow v1b")
                break

    @workflow.signal
    async def do_next_signal(self, signal: str) -> None:
        """Signal to perform next action."""
        self.signals.append(signal)


@workflow.defn(name="Pinned", versioning_behavior=common.VersioningBehavior.PINNED)
class PinnedWorkflowV1:
    """PinnedWorkflowV1 demonstrates a workflow that likely has a short lifetime, and we want to always
    stay pinned to the same version it began on.

    Note that generally you won't want or need to include a version number in your workflow name if
    you're using the worker versioning feature. This sample does it to illustrate changes to the
    same code over time - but really what we're demonstrating here is the evolution of what would
    have been one workflow definition.
    """

    def __init__(self) -> None:
        self.signals: list[str] = []

    @workflow.run
    async def run(self) -> None:
        workflow.logger.info(
            "Pinned Workflow v1 started.", extra={"StartTime": workflow.now()}
        )

        while True:
            await workflow.wait_condition(lambda: len(self.signals) > 0)
            signal = self.signals.pop(0)
            if signal == "conclude":
                break

        await workflow.execute_activity(
            some_activity,
            "Pinned-v1",
            start_to_close_timeout=timedelta(seconds=10),
        )

    @workflow.signal
    async def do_next_signal(self, signal: str) -> None:
        """Signal to perform next action."""
        self.signals.append(signal)


@workflow.defn(name="Pinned", versioning_behavior=common.VersioningBehavior.PINNED)
class PinnedWorkflowV2:
    """PinnedWorkflowV2 has changes that would make it incompatible with v1, and aren't protected by
    a patch.
    """

    def __init__(self) -> None:
        self.signals: list[str] = []

    @workflow.run
    async def run(self) -> None:
        workflow.logger.info(
            "Pinned Workflow v2 started.", extra={"StartTime": workflow.now()}
        )

        # Here we call an activity where we didn't before, which is an incompatible change.
        await workflow.execute_activity(
            some_activity,
            "Pinned-v2",
            start_to_close_timeout=timedelta(seconds=10),
        )

        while True:
            await workflow.wait_condition(lambda: len(self.signals) > 0)
            signal = self.signals.pop(0)
            if signal == "conclude":
                break

        # We've also changed the activity type here, another incompatible change
        await workflow.execute_activity(
            some_incompatible_activity,
            IncompatibleActivityInput(called_by="Pinned-v2", more_data="hi"),
            start_to_close_timeout=timedelta(seconds=10),
        )

    @workflow.signal
    async def do_next_signal(self, signal: str) -> None:
        """Signal to perform next action."""
        self.signals.append(signal)

"""Workflows and activities used by the Redis external storage sample tests."""

from __future__ import annotations

from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

LARGE = "x" * 356  # ~358 bytes as a JSON string, above the 256-byte test threshold
LARGE_2 = "y" * 356  # distinct large payload with a different SHA-256 hash


@activity.defn
async def large_io_activity(_data: str) -> str:
    return LARGE


@activity.defn
async def large_output_activity() -> str:
    """Return a large payload with no retries; used to test store failures."""
    return LARGE


@workflow.defn
class LargeOutputNoRetryWorkflow:
    """Execute one activity that returns a large payload with no retries."""

    @workflow.run
    async def run(self) -> str:
        return await workflow.execute_activity(
            large_output_activity,
            schedule_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )


@workflow.defn
class LargeIOWorkflow:
    """Pass workflow input to an activity and return a large output."""

    @workflow.run
    async def run(self, data: str) -> str:
        await workflow.execute_activity(
            large_io_activity,
            data,
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        return LARGE


@activity.defn
async def download_document(document_id: str) -> str:
    """Download the raw document content from remote storage."""
    del document_id
    return LARGE


@activity.defn
async def extract_text(raw_content: str) -> str:
    """Extract and normalize text from the raw document content."""
    del raw_content
    return LARGE_2


@activity.defn
async def index_document(text: str) -> str:
    """Index the extracted text into the search index."""
    del text
    return "idx-00001"


@workflow.defn
class DocumentIngestionWorkflow:
    """Download, extract, and index a document through large payload hops."""

    @workflow.run
    async def run(self, document_id: str) -> str:
        raw_content = await workflow.execute_activity(
            download_document,
            document_id,
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        extracted_text = await workflow.execute_activity(
            extract_text,
            raw_content,
            schedule_to_close_timeout=timedelta(seconds=10),
        )
        return await workflow.execute_activity(
            index_document,
            extracted_text,
            schedule_to_close_timeout=timedelta(seconds=10),
        )


@workflow.defn
class ChildWorkflow:
    @workflow.run
    async def run(self, data: str) -> str:
        return f"{len(data)}"


@workflow.defn
class ParentWithChildWorkflow:
    """Delegate work to a child workflow whose ID is ``{parent_id}-child``."""

    @workflow.run
    async def run(self) -> str:
        child_id = f"{workflow.info().workflow_id}-child"
        return await workflow.execute_child_workflow(
            ChildWorkflow.run,
            LARGE,
            id=child_id,
            execution_timeout=timedelta(seconds=10),
        )


@workflow.defn
class PaymentProcessingWorkflow:
    """Process payment for an order and return a large confirmation payload."""

    @workflow.run
    async def run(self, order_details: str) -> str:
        del order_details
        return LARGE_2


@workflow.defn
class OrderFulfillmentWorkflow:
    """Coordinate order fulfillment by delegating payment to a child workflow."""

    @workflow.run
    async def run(self, order_details: str) -> str:
        payment_id = f"{workflow.info().workflow_id}-payment"
        return await workflow.execute_child_workflow(
            PaymentProcessingWorkflow.run,
            order_details,
            id=payment_id,
            execution_timeout=timedelta(seconds=10),
        )


@workflow.defn
class ModelTrainingWorkflow:
    """Simulate a long-running training job with large cross-boundary payloads."""

    def __init__(self) -> None:
        self._done = False

    @workflow.run
    async def run(self, training_config: str) -> str:
        del training_config
        await workflow.wait_condition(lambda: self._done)
        return LARGE

    @workflow.signal
    async def apply_overrides(self, override_params: str) -> None:
        """Inject updated configuration into the running training job."""
        del override_params

    @workflow.signal
    async def complete(self) -> None:
        self._done = True

    @workflow.update
    async def get_metrics(self, checkpoint_id: str) -> str:
        """Return the current training metrics snapshot."""
        del checkpoint_id
        return LARGE_2


@workflow.defn
class SignalQueryUpdateWorkflow:
    """Long-running workflow that accepts a signal, query, and update."""

    def __init__(self) -> None:
        self._done = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self._done)
        return LARGE

    @workflow.signal
    async def finish(self, _data: str) -> None:
        self._done = True

    @workflow.query
    def get_value(self, _data: str) -> str:
        return LARGE

    @workflow.update
    async def do_update(self, _data: str) -> str:
        return LARGE

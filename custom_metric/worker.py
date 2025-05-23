import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio import activity
from temporalio.client import Client
from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
    Worker,
)

from custom_metric.activity import print_and_sleep
from custom_metric.workflow import StartTwoActivitiesWorkflow


class SimpleWorkerInterceptor(Interceptor):
    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return CustomScheduleToStartInterceptor(next)


class CustomScheduleToStartInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput):

        schedule_to_start = (
            activity.info().started_time
            - activity.info().current_attempt_scheduled_time
        )
        # Could do the original schedule time instead of current attempt
        # schedule_to_start_second_option = activity.info().started_time - activity.info().scheduled_time

        meter = activity.metric_meter()
        histogram = meter.create_histogram_timedelta(
            "custom_activity_schedule_to_start_latency",
            description="Time between activity scheduling and start",
            unit="duration",
        )
        histogram.record(
            schedule_to_start, {"workflow_type": activity.info().workflow_type}
        )
        return await self.next.execute_activity(input)


async def main():
    runtime = Runtime(
        telemetry=TelemetryConfig(metrics=PrometheusConfig(bind_address="0.0.0.0:9090"))
    )
    client = await Client.connect(
        "localhost:7233",
        runtime=runtime,
    )
    worker = Worker(
        client,
        task_queue="custom-metric-task-queue",
        interceptors=[SimpleWorkerInterceptor()],
        workflows=[StartTwoActivitiesWorkflow],
        activities=[print_and_sleep],
        # only one activity executor with two concurrently scheduled activities
        # to force a nontrivial schedule to start times
        activity_executor=ThreadPoolExecutor(1),
        max_concurrent_activities=1,
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

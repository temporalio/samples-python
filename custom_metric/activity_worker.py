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


@activity.defn
def print_message():
    print("in the activity")


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
        activities=[print_message],
        activity_executor=ThreadPoolExecutor(5),
        interceptors=[SimpleWorkerInterceptor()],
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

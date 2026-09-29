import asyncio
import logging

from pythonjsonlogger import json
from temporalio.runtime import Runtime, TelemetryConfig, LogForwardingConfig, LoggingConfig
from temporalio.worker import Worker
from temporalio.client import Client

from benign_application_error.workflow import BenignApplicationErrorWorkflow
from benign_application_error.activities import greeting_activities


def configure_json_logger() -> logging.Logger:
    logger = logging.getLogger()
#     logger.setLevel(logging.DEBUG) # set level to DEBUG and observe the difference
    handler = logging.StreamHandler()
    handler.setFormatter(json.JsonFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger

def set_init_runtime() -> Runtime:
    app_err_logger = configure_json_logger()

    return  Runtime(
                    telemetry=TelemetryConfig(
                               logging=LoggingConfig(
                                    LoggingConfig.default.filter,
                                    forwarding=LogForwardingConfig(logger = app_err_logger),
                               )
                          )
                    )


async def main():
    # Configuring logger
    runtime = set_init_runtime()

    client = await Client.connect(
            "localhost:7233",
            runtime=runtime,
    )

    worker = Worker(
        client=client,
        task_queue="benign_application_error_task_queue",
        workflows=[BenignApplicationErrorWorkflow],
        activities=[greeting_activities],
    )
    print("running worker....")

    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
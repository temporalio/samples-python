from temporalio.common import WorkerDeploymentVersion
from temporalio.contrib.aws.lambda_worker import LambdaWorkerConfig, run_worker
from temporalio.contrib.aws.lambda_worker.otel import apply_defaults

from activities import record_response
from models import TASK_QUEUE


def configure(config: LambdaWorkerConfig) -> None:
    config.worker_config["task_queue"] = TASK_QUEUE
    # Activity-only Lambda worker. Votes are standalone activities invoked
    # directly by the client;
    config.worker_config["activities"] = [record_response]
    apply_defaults(config)


lambda_handler = run_worker(
    WorkerDeploymentVersion(deployment_name="survey-poll-SA", build_id="v1"),
    configure,
)

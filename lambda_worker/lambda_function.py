from activities import hello_activity, process_vote_activity
from temporalio.common import WorkerDeploymentVersion
from temporalio.contrib.aws.lambda_worker import LambdaWorkerConfig, run_worker
from temporalio.contrib.aws.lambda_worker.otel import apply_defaults
from workflows import TASK_QUEUE, SampleWorkflow, VoteProcessingWorkflow


def configure(config: LambdaWorkerConfig) -> None:
    config.worker_config["task_queue"] = TASK_QUEUE
    config.worker_config["workflows"] = [SampleWorkflow, VoteProcessingWorkflow]
    config.worker_config["activities"] = [hello_activity, process_vote_activity]
    config.worker_config["max_concurrent_activities"] = 1
    apply_defaults(config)


lambda_handler = run_worker(
    WorkerDeploymentVersion(deployment_name="hello-world", build_id="build-4"),
    configure,
)

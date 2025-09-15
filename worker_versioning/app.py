"""Main application for the worker versioning sample."""

import asyncio
import logging
import uuid

from temporalio.client import Client

from worker_versioning.constants import DEPLOYMENT_NAME, TASK_QUEUE

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    client = await Client.connect("localhost:7233")

    # Wait for v1 worker and set as current version
    logging.info(
        "Waiting for v1 worker to appear. Run `python worker_versioning/workerv1.py` in another terminal"
    )
    await wait_for_worker_and_make_current(client, "1.0")

    # Start auto-upgrading and pinned workflows
    auto_upgrade_workflow_id = "worker-versioning-versioning-autoupgrade_" + str(
        uuid.uuid4()
    )
    auto_upgrade_execution = await client.start_workflow(
        "AutoUpgrading",
        id=auto_upgrade_workflow_id,
        task_queue=TASK_QUEUE,
    )

    pinned_workflow_id = "worker-versioning-versioning-pinned_" + str(uuid.uuid4())
    pinned_execution = await client.start_workflow(
        "Pinned",
        id=pinned_workflow_id,
        task_queue=TASK_QUEUE,
    )

    logging.info("Started auto-upgrading workflow: %s", auto_upgrade_execution.id)
    logging.info("Started pinned workflow: %s", pinned_execution.id)

    # Signal both workflows a few times to drive them
    await advance_workflows(auto_upgrade_execution, pinned_execution)

    # Now wait for the v1.1 worker to appear and become current
    logging.info(
        "Waiting for v1.1 worker to appear. Run `python worker_versioning/workerv1_1.py` in another terminal"
    )
    await wait_for_worker_and_make_current(client, "1.1")

    # Once it has, we will continue to advance the workflows.
    # The auto-upgrade workflow will now make progress on the new worker, while the pinned one will
    # keep progressing on the old worker.
    await advance_workflows(auto_upgrade_execution, pinned_execution)

    # Finally we'll start the v2 worker, and again it'll become the new current version
    logging.info(
        "Waiting for v2 worker to appear. Run `python worker_versioning/workerv2.py` in another terminal"
    )
    await wait_for_worker_and_make_current(client, "2.0")

    # Once it has we'll start one more new workflow, another pinned one, to demonstrate that new
    # pinned workflows start on the current version.
    pinned_workflow_2_id = "worker-versioning-versioning-pinned-2_" + str(uuid.uuid4())
    pinned_execution_2 = await client.start_workflow(
        "Pinned",
        id=pinned_workflow_2_id,
        task_queue=TASK_QUEUE,
    )
    logging.info("Started pinned workflow v2: %s", pinned_execution_2.id)

    # Now we'll conclude all workflows. You should be able to see in your server UI that the pinned
    # workflow always stayed on 1.0, while the auto-upgrading workflow migrated.
    for handle in [auto_upgrade_execution, pinned_execution, pinned_execution_2]:
        await handle.signal("do_next_signal", "conclude")
        await handle.result()

    logging.info("All workflows completed")


async def advance_workflows(auto_upgrade_execution, pinned_execution):
    """Signal both workflows a few times to drive them."""
    for i in range(3):
        await auto_upgrade_execution.signal("do_next_signal", "do-activity")
        await pinned_execution.signal("do_next_signal", "some-signal")


async def wait_for_worker_and_make_current(client: Client, build_id: str) -> None:
    import temporalio.api.workflowservice.v1 as wsv1
    from temporalio.common import WorkerDeploymentVersion

    target_version = WorkerDeploymentVersion(
        deployment_name=DEPLOYMENT_NAME, build_id=build_id
    )

    # Wait for the worker to appear
    while True:
        try:
            describe_request = wsv1.DescribeWorkerDeploymentRequest(
                namespace=client.namespace,
                deployment_name=DEPLOYMENT_NAME,
            )
            response = await client.workflow_service.describe_worker_deployment(
                describe_request
            )

            # Check if our version is present in the version summaries
            for version_summary in response.worker_deployment_info.version_summaries:
                if (
                    version_summary.deployment_version.deployment_name
                    == target_version.deployment_name
                    and version_summary.deployment_version.build_id
                    == target_version.build_id
                ):
                    break
            else:
                await asyncio.sleep(1)
                continue

            break

        except Exception:
            await asyncio.sleep(1)
            continue

    # Once the version is available, set it as current
    set_request = wsv1.SetWorkerDeploymentCurrentVersionRequest(
        namespace=client.namespace,
        deployment_name=DEPLOYMENT_NAME,
        build_id=target_version.build_id,
    )
    await client.workflow_service.set_worker_deployment_current_version(set_request)


if __name__ == "__main__":
    asyncio.run(main())

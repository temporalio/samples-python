import asyncio

from temporalio.client import Client, WorkflowUpdateFailedError
from temporalio.envconfig import ClientConfig
from temporalio.exceptions import ApplicationError

from reqrespupdate import WORKFLOW_ID
from reqrespupdate.workflow import BACKOFF_ERROR_TYPE, Request, UppercaseWorkflow


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)
    handle = client.get_workflow_handle(WORKFLOW_ID)

    # Request an uppercasing every second. Several of these can be run at once,
    # in separate terminals, to confirm the requesters are independent of each
    # other.
    i = 0
    while True:
        request = Request(input=f"foo{i}")
        try:
            response = await handle.execute_update(UppercaseWorkflow.uppercase, request)
            print(f"Requested uppercase of {request.input}, got {response.output}")
            i += 1
        except WorkflowUpdateFailedError as err:
            # The run we sent to is draining toward a continue-as-new and asked
            # us to back off. Retrying sends to the same workflow ID, which by
            # then is the new run. Any other failure is a real one.
            if (
                isinstance(err.cause, ApplicationError)
                and err.cause.type == BACKOFF_ERROR_TYPE
            ):
                print("Rejected while the workflow continues as new, retrying")
            else:
                raise
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())

import temporalio.api
import temporalio.api.common
import temporalio.api.common.v1
import temporalio.api.enums.v1
import temporalio.api.nexus
import temporalio.api.nexus.v1
import temporalio.api.operatorservice
import temporalio.api.operatorservice.v1
from temporalio.client import Client


# TODO: copied from sdk-python tests/helpers/nexus
async def create_nexus_endpoint(
    name: str, task_queue: str, client: Client
) -> temporalio.api.operatorservice.v1.CreateNexusEndpointResponse:
    return await client.operator_service.create_nexus_endpoint(
        temporalio.api.operatorservice.v1.CreateNexusEndpointRequest(
            spec=temporalio.api.nexus.v1.EndpointSpec(
                name=name,
                target=temporalio.api.nexus.v1.EndpointTarget(
                    worker=temporalio.api.nexus.v1.EndpointTarget.Worker(
                        namespace=client.namespace,
                        task_queue=task_queue,
                    )
                ),
            )
        )
    )


async def delete_nexus_endpoint(
    id: str, version: int, client: Client
) -> temporalio.api.operatorservice.v1.DeleteNexusEndpointResponse:
    return await client.operator_service.delete_nexus_endpoint(
        temporalio.api.operatorservice.v1.DeleteNexusEndpointRequest(
            id=id,
            version=version,
        )
    )

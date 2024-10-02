from typing import Any
from uuid import uuid4

temporal_client: Any = None
CartWorkflow: Any = None
RequestHandlerWithAsyncCompensationWorkflow: Any = None
RequestHandlerUpdate: Any = None
ShoppingCartUpdate: Any = None
Response: Any = None
my_task_queue: Any = None


# Option A: extend ExecuteUpdate

# update-maybe-running-workflow
async def handle_add_to_shopping_cart_http_request_A(request):
    cart_id = request.session.data.get("cart_id")
    
    workflow_handle = temporal_client.prepare_start_workflow(
		CartWorkflow,
		id=cart_id,
        task_queue=my_task_queue,
	)
    new_cart_state = await temporal_client.execute_update(
        ShoppingCartUpdate, arg=request.json(), start_workflow=workflow_handle,
    )
    # Reviewer> OK, this makes sense: we're updating the cart, and creating it
    #           if it doesn't exist.
    
    return Response(new_cart_state)


# start-workflow-and-do-update
async def handle_http_request_with_async_compensation_A(request):

    workflow_id = uuid4().hex
    workflow_handle = temporal_client.prepare_start_workflow(
		RequestHandlerWithAsyncCompensationWorkflow,
		id=workflow_id,
        task_queue=my_task_queue,
	)
    response_value = await temporal_client.execute_update(
        RequestHandlerUpdate, arg=request.json(), start_workflow=workflow_handle,
    )
    # Reviewer> OK, this makes sense: we're kicking off the workflow that does
    #           the async compensation, and using this update to get an initial
    #           syncronous response.
    
    return Response(response_value, workflow_id)


# Option B: extend StartWorkflow

## update-maybe-running-workflow
async def handle_add_to_shopping_cart_http_request_B(request):
    cart_id = request.session.data.get("cart_id")
    
    update_handle = temporal_client.prepare_execute_update(
        ShoppingCartUpdate, arg=request.json()
    )
    # Reviewer> OK, this makes sense: We're going to update the cart.

    await temporal_client.start_workflow(       
        CartWorkflow, cart_id, start_update=update_handle
    )
    # Reviewer> Hang on, if the cart exists already why are we starting the
    #           CartWorkflow? Don't we just want to do an update in that case?
    
    # Author>   Don't worry, this is just what you have to do with Temporal. If
    #           the workflow exists already it's fine.

    new_cart_state = await update_handle.result()
    
    # Reviewer> Hang on, I thought the update features Temporal released
    #           recently were geared for low-latency use cases. Why are we doing
    #           two RPCs to get the new shopping cart state?
    
    # Author>   Don't worry, Temporal guarantees that there's no RPC here,
    #           because we used `prepare_execute_update` above. (If we'd used
    #           `prepare_start_update` there probably would be an RPC here,
    #           although it's possible there wouldn't be.)
    
    return Response(new_cart_state)


## start-workflow-and-do-update
async def handle_http_request_with_async_compensation_B(request):
    
    update_handle = temporal_client.prepare_execute_update(
        RequestHandlerUpdate, arg=request.json()
    )
    # Reviewer> OK, this makes sense: this is the update that's going to get the synchronous response.

    workflow_id = uuid4().hex
    await temporal_client.start_workflow(       
        RequestHandlerWithAsyncCompensationWorkflow, id=workflow_id, start_update=update_handle
    )

    response_value = await update_handle.result()

    # Reviewer> Hang on, I thought the update features Temporal released
    #           recently were geared for low-latency use cases. Why are we doing
    #           two RPCs to get the response?
    
    # Author>   Don't worry, Temporal guarantees that there's no RPC here,
    #           because we used `prepare_execute_update` above. (If we'd used
    #           `prepare_start_update` there probably would be an RPC here,
    #           although it's possible there wouldn't be.)
        
    return Response(response_value, workflow_id)

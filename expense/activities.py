import httpx
from temporalio import activity

from expense import EXPENSE_SERVER_HOST_PORT


@activity.defn
async def create_expense_activity(expense_id: str) -> None:
    if not expense_id:
        raise ValueError("expense id is empty")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{EXPENSE_SERVER_HOST_PORT}/create",
            params={"is_api_call": "true", "id": expense_id},
        )
        response.raise_for_status()
        body = response.text

    if body == "SUCCEED":
        activity.logger.info(f"Expense created. ExpenseID: {expense_id}")
        return

    raise Exception(body)


@activity.defn
async def wait_for_decision_activity(expense_id: str) -> str:
    """
    Wait for the expense decision. This activity will complete asynchronously. When this function
    raises activity.AsyncActivityCompleteError, the Temporal Python SDK recognizes this error, and won't mark this activity
    as failed or completed. The Temporal server will wait until Client.complete_activity() is called or timeout happened
    whichever happen first. In this sample case, the complete_activity() method is called by our sample expense system when
    the expense is approved.
    """
    if not expense_id:
        raise ValueError("expense id is empty")

    logger = activity.logger

    # Save current activity info so it can be completed asynchronously when expense is approved/rejected
    activity_info = activity.info()
    task_token = activity_info.task_token

    register_callback_url = f"{EXPENSE_SERVER_HOST_PORT}/registerCallback"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            register_callback_url,
            params={"id": expense_id},
            data={"task_token": task_token.hex()},
        )
        response.raise_for_status()
        body = response.text

    status = body
    if status == "SUCCEED":
        # register callback succeed
        logger.info(f"Successfully registered callback. ExpenseID: {expense_id}")

        # Raise the complete-async error which will return from this function but
        # does not mark the activity as complete from the workflow perspective.
        #
        # Activity completion is signaled in the `notify_expense_state_change`
        # function in `ui.py`.
        activity.raise_complete_async()

    logger.warning(f"Register callback failed. ExpenseStatus: {status}")
    raise Exception(f"register callback failed status: {status}")


@activity.defn
async def payment_activity(expense_id: str) -> None:
    if not expense_id:
        raise ValueError("expense id is empty")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{EXPENSE_SERVER_HOST_PORT}/action",
            params={"is_api_call": "true", "type": "payment", "id": expense_id},
        )
        response.raise_for_status()
        body = response.text

    if body == "SUCCEED":
        activity.logger.info(f"payment_activity succeed ExpenseID: {expense_id}")
        return

    raise Exception(body)

import httpx
from temporalio import activity

from openai_agents_expense import EXPENSE_SERVER_HOST_PORT
from openai_agents_expense.models import (
    ExpenseProcessingResult,
    ExpenseReport,
    UpdateExpenseActivityInput,
)


@activity.defn
async def create_expense_activity(expense_report: ExpenseReport) -> None:
    """
    Create a new expense entry in the expense system.
    """

    expense_id = expense_report.expense_id

    # Activity start logging
    activity.logger.info(
        "📝 CREATE_EXPENSE_START: Creating expense entry",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "start",
        },
    )

    if not expense_id:
        activity.logger.error(
            "🚨 CREATE_EXPENSE_ERROR: Empty expense ID",
            extra={
                "expense_id": expense_id,
                "activity": "create_expense_activity",
                "stage": "validation_error",
                "error": "expense id is empty",
            },
        )
        raise ValueError("expense id is empty")

    activity.logger.info(
        "🌐 HTTP_REQUEST: Making HTTP request to expense server",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "http_request",
            "url": f"{EXPENSE_SERVER_HOST_PORT}/create",
        },
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{EXPENSE_SERVER_HOST_PORT}/create/{expense_id}",
        )
        response.raise_for_status()
        body = response.text

    activity.logger.info(
        "📨 HTTP_RESPONSE: Received response from expense server",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "http_response",
            "response_text": body,
            "status_code": response.status_code,
        },
    )

    # To ensure the activity is idempotent, we accept the case where the expense id already exists
    if body == "SUCCEED" or body == "ERROR:ID_ALREADY_EXISTS":
        activity.logger.info(
            "✅ CREATE_EXPENSE_SUCCESS: Expense entry created successfully",
            extra={
                "expense_id": expense_id,
                "activity": "create_expense_activity",
                "stage": "success",
            },
        )
        return

    activity.logger.error(
        "🚨 CREATE_EXPENSE_FAILURE: Failed to create expense entry",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "failure",
            "response_text": body,
        },
    )
    raise Exception(body)


@activity.defn
async def update_expense_activity(
    update_expense_activity_input: UpdateExpenseActivityInput,
) -> None:
    """
    Update the expense entry in the expense system.
    """
    async with httpx.AsyncClient() as client:
        expense_processing_result = ExpenseProcessingResult(
            expense_report=update_expense_activity_input.expense_report,
            categorization=update_expense_activity_input.categorization,
            policy_evaluation=update_expense_activity_input.policy_evaluation,
            fraud_assessment=update_expense_activity_input.fraud_assessment,
            agent_decision=update_expense_activity_input.agent_decision,
        )

        response = await client.post(
            f"{EXPENSE_SERVER_HOST_PORT}/update/{update_expense_activity_input.expense_id}",
            json=expense_processing_result.model_dump(mode='json'),
        )
        response.raise_for_status()
        body = response.text

    if body == "SUCCEED":
        activity.logger.info(
            "✅ UPDATE_EXPENSE_SUCCESS: Expense entry updated successfully",
        )
    else:
        activity.logger.error(
            "🚨 UPDATE_EXPENSE_FAILURE: Failed to update expense entry",
        )
        raise Exception(body)


@activity.defn
async def wait_for_decision_activity(expense_id: str) -> str:
    """
    Wait for the expense decision. This activity will complete asynchronously. When this function
    calls activity.raise_complete_async(), the Temporal Python SDK recognizes this and won't mark this activity
    as failed or completed. The Temporal server will wait until Client.complete_activity() is called or timeout happened
    whichever happen first. In this sample case, the complete_activity() method is called by our sample expense system when
    the expense is approved.
    """

    # Activity start logging
    activity.logger.info(
        "⏳ WAIT_DECISION_START: Starting async wait for human decision",
        extra={
            "expense_id": expense_id,
            "activity": "wait_for_decision_activity",
            "stage": "start",
            "async_completion": True,
        },
    )

    if not expense_id:
        activity.logger.error(
            "🚨 WAIT_DECISION_ERROR: Empty expense ID",
            extra={
                "expense_id": expense_id,
                "activity": "wait_for_decision_activity",
                "stage": "validation_error",
                "error": "expense id is empty",
            },
        )
        raise ValueError("expense id is empty")

    # Save current activity info so it can be completed asynchronously when expense is approved/rejected
    activity_info = activity.info()
    task_token = activity_info.task_token

    activity.logger.info(
        "🔑 TASK_TOKEN: Generated task token for async completion",
    )

    # activity.logger.info(
    #     f"📞 CALLBACK_REGISTRATION: Registering callback for async completion",
    #     extra={
    #         "expense_id": expense_id,
    #         "activity": "wait_for_decision_activity",
    #         "stage": "callback_registration",
    #         "callback_url": register_callback_url,
    #     },
    # )

    request_review_url = f"{EXPENSE_SERVER_HOST_PORT}/request_review/{expense_id}"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            request_review_url,
            data={"task_token": task_token.hex()},
        )
        response.raise_for_status()
        body = response.text

    # activity.logger.info(
    #     f"📨 CALLBACK_RESPONSE: Received callback registration response",
    #     extra={
    #         "expense_id": expense_id,
    #         "activity": "wait_for_decision_activity",
    #         "stage": "callback_response",
    #         "response_text": body,
    #         "status_code": response.status_code,
    #     },
    # )

    status = body
    if status == "SUCCEED":
        # register callback succeed
        activity.logger.info(
            "✅ CALLBACK_SUCCESS: Callback registered successfully, entering async wait",
            extra={
                "expense_id": expense_id,
                "activity": "wait_for_decision_activity",
                "stage": "callback_success",
                "async_completion_mode": True,
            },
        )

        # Raise the complete-async error which will return from this function but
        # does not mark the activity as complete from the workflow perspective.
        #
        # Activity completion is signaled in the `notify_expense_state_change`
        # function in `ui.py`.
        activity.raise_complete_async()
    else:
        activity.logger.error(
            "🚨 WAIT_DECISION_FAILURE: Wait for decision activity failed",
        )
        raise Exception(f"request review failed status: {status}")


@activity.defn
async def payment_activity(expense_id: str) -> None:
    """
    Process payment for an approved expense.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{EXPENSE_SERVER_HOST_PORT}/payment/{expense_id}",
        )
        response.raise_for_status()
        body = response.text

    if body == "SUCCEED":
        activity.logger.info(
            "✅ PAYMENT_SUCCESS: Payment processed successfully",
            extra={
                "expense_id": expense_id,
                "activity": "payment_activity",
                "stage": "success",
            },
        )
        return
    else:
        activity.logger.error(
            "🚨 PAYMENT_FAILURE: Payment processing failed",
        )
        raise Exception(body)

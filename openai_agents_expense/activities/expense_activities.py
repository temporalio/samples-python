import httpx
from temporalio import activity

from openai_agents_expense import EXPENSE_SERVER_HOST_PORT


@activity.defn
async def create_expense_activity(expense_id: str) -> None:
    """
    Create a new expense entry in the expense system.
    """
    
    # Activity start logging
    activity.logger.info(
        f"📝 CREATE_EXPENSE_START: Creating expense entry",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "start"
        }
    )
    
    if not expense_id:
        activity.logger.error(
            f"🚨 CREATE_EXPENSE_ERROR: Empty expense ID",
            extra={
                "expense_id": expense_id,
                "activity": "create_expense_activity",
                "stage": "validation_error",
                "error": "expense id is empty"
            }
        )
        raise ValueError("expense id is empty")

    activity.logger.info(
        f"🌐 HTTP_REQUEST: Making HTTP request to expense server",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "http_request",
            "url": f"{EXPENSE_SERVER_HOST_PORT}/create"
        }
    )
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{EXPENSE_SERVER_HOST_PORT}/create",
            params={"is_api_call": "true", "id": expense_id},
        )
        response.raise_for_status()
        body = response.text

    activity.logger.info(
        f"📨 HTTP_RESPONSE: Received response from expense server",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "http_response",
            "response_text": body,
            "status_code": response.status_code
        }
    )

    if body == "SUCCEED":
        activity.logger.info(
            f"✅ CREATE_EXPENSE_SUCCESS: Expense entry created successfully",
            extra={
                "expense_id": expense_id,
                "activity": "create_expense_activity",
                "stage": "success"
            }
        )
        return

    activity.logger.error(
        f"🚨 CREATE_EXPENSE_FAILURE: Failed to create expense entry",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "failure",
            "response_text": body
        }
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
        f"⏳ WAIT_DECISION_START: Starting async wait for human decision",
        extra={
            "expense_id": expense_id,
            "activity": "wait_for_decision_activity",
            "stage": "start",
            "async_completion": True
        }
    )
    
    if not expense_id:
        activity.logger.error(
            f"🚨 WAIT_DECISION_ERROR: Empty expense ID",
            extra={
                "expense_id": expense_id,
                "activity": "wait_for_decision_activity",
                "stage": "validation_error",
                "error": "expense id is empty"
            }
        )
        raise ValueError("expense id is empty")

    # Save current activity info so it can be completed asynchronously when expense is approved/rejected
    activity_info = activity.info()
    task_token = activity_info.task_token

    activity.logger.info(
        f"🔑 TASK_TOKEN: Generated task token for async completion",
        extra={
            "expense_id": expense_id,
            "activity": "wait_for_decision_activity",
            "stage": "task_token_generation",
            "task_token_length": len(task_token.hex()),
            "workflow_id": activity_info.workflow_id,
            "activity_id": activity_info.activity_id
        }
    )

    register_callback_url = f"{EXPENSE_SERVER_HOST_PORT}/registerCallback"

    activity.logger.info(
        f"📞 CALLBACK_REGISTRATION: Registering callback for async completion",
        extra={
            "expense_id": expense_id,
            "activity": "wait_for_decision_activity",
            "stage": "callback_registration",
            "callback_url": register_callback_url
        }
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            register_callback_url,
            params={"id": expense_id},
            data={"task_token": task_token.hex()},
        )
        response.raise_for_status()
        body = response.text

    activity.logger.info(
        f"📨 CALLBACK_RESPONSE: Received callback registration response",
        extra={
            "expense_id": expense_id,
            "activity": "wait_for_decision_activity",
            "stage": "callback_response",
            "response_text": body,
            "status_code": response.status_code
        }
    )

    status = body
    if status == "SUCCEED":
        # register callback succeed
        activity.logger.info(
            f"✅ CALLBACK_SUCCESS: Callback registered successfully, entering async wait",
            extra={
                "expense_id": expense_id,
                "activity": "wait_for_decision_activity",
                "stage": "callback_success",
                "async_completion_mode": True
            }
        )

        # Raise the complete-async error which will return from this function but
        # does not mark the activity as complete from the workflow perspective.
        #
        # Activity completion is signaled in the `notify_expense_state_change`
        # function in `ui.py`.
        activity.raise_complete_async()

    activity.logger.warning(
        f"⚠️ CALLBACK_FAILURE: Failed to register callback",
        extra={
            "expense_id": expense_id,
            "activity": "wait_for_decision_activity",
            "stage": "callback_failure",
            "response_status": status
        }
    )
    
    activity.logger.error(
        f"🚨 WAIT_DECISION_FAILURE: Wait for decision activity failed",
        extra={
            "expense_id": expense_id,
            "activity": "wait_for_decision_activity",
            "stage": "failure",
            "response_status": status
        }
    )
    raise Exception(f"register callback failed status: {status}")


@activity.defn
async def payment_activity(expense_id: str) -> None:
    """
    Process payment for an approved expense.
    """
    
    # Activity start logging
    activity.logger.info(
        f"💳 PAYMENT_START: Starting payment processing",
        extra={
            "expense_id": expense_id,
            "activity": "payment_activity",
            "stage": "start"
        }
    )
    
    if not expense_id:
        activity.logger.error(
            f"🚨 PAYMENT_ERROR: Empty expense ID",
            extra={
                "expense_id": expense_id,
                "activity": "payment_activity",
                "stage": "validation_error",
                "error": "expense id is empty"
            }
        )
        raise ValueError("expense id is empty")

    activity.logger.info(
        f"🌐 HTTP_REQUEST: Making payment request to expense server",
        extra={
            "expense_id": expense_id,
            "activity": "payment_activity",
            "stage": "http_request",
            "url": f"{EXPENSE_SERVER_HOST_PORT}/action"
        }
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{EXPENSE_SERVER_HOST_PORT}/action",
            params={
                "is_api_call": "true",
                "type": "payment",
                "id": expense_id,
            },
        )
        response.raise_for_status()
        body = response.text

    activity.logger.info(
        f"📨 HTTP_RESPONSE: Received payment response from expense server",
        extra={
            "expense_id": expense_id,
            "activity": "payment_activity",
            "stage": "http_response",
            "response_text": body,
            "status_code": response.status_code
        }
    )

    if body == "SUCCEED":
        activity.logger.info(
            f"✅ PAYMENT_SUCCESS: Payment processed successfully",
            extra={
                "expense_id": expense_id,
                "activity": "payment_activity",
                "stage": "success"
            }
        )
        return

    activity.logger.error(
        f"🚨 PAYMENT_FAILURE: Payment processing failed",
        extra={
            "expense_id": expense_id,
            "activity": "payment_activity",
            "stage": "failure",
            "response_text": body
        }
    )
    raise Exception(body) 
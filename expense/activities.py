import httpx
from temporalio import activity
from temporalio.exceptions import ApplicationError

from expense import EXPENSE_SERVER_HOST_PORT

# Module-level HTTP client, managed by worker lifecycle
_http_client: httpx.AsyncClient | None = None


async def initialize_http_client() -> None:
    """Initialize the global HTTP client. Called by worker setup."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient()


async def cleanup_http_client() -> None:
    """Cleanup the global HTTP client. Called by worker shutdown."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
    _http_client = None


def get_http_client() -> httpx.AsyncClient:
    """Get the global HTTP client."""
    if _http_client is None:
        raise RuntimeError(
            "HTTP client not initialized. Call initialize_http_client() first."
        )
    return _http_client


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
            "stage": "start",
        },
    )

    if not expense_id:
        activity.logger.error(
            f"🚨 CREATE_EXPENSE_ERROR: Empty expense ID",
            extra={
                "expense_id": expense_id,
                "activity": "create_expense_activity",
                "stage": "validation_error",
                "error": "expense id is empty",
            },
        )
        raise ValueError("expense id is empty")

    client = get_http_client()
    try:
        response = await client.get(
            f"{EXPENSE_SERVER_HOST_PORT}/create",
            params={"is_api_call": "true", "id": expense_id},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if 400 <= e.response.status_code < 500:
            raise ApplicationError(
                f"Client error: {e.response.status_code} {e.response.text}",
                non_retryable=True,
            ) from e
        raise

    body = response.text

    activity.logger.info(
        f"📨 HTTP_RESPONSE: Received response from expense server",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "http_response",
            "response_text": body,
            "status_code": response.status_code,
        },
    )

    if body == "SUCCEED":
        activity.logger.info(
            f"✅ CREATE_EXPENSE_SUCCESS: Expense entry created successfully",
            extra={
                "expense_id": expense_id,
                "activity": "create_expense_activity",
                "stage": "success",
            },
        )
        return

    activity.logger.error(
        f"🚨 CREATE_EXPENSE_FAILURE: Failed to create expense entry",
        extra={
            "expense_id": expense_id,
            "activity": "create_expense_activity",
            "stage": "failure",
            "response_text": body,
        },
    )
    raise Exception(body)


@activity.defn
async def register_for_decision_activity(expense_id: str) -> None:
    """
    Register the expense for decision. This activity registers the workflow
    with the external system so it can receive signals when decisions are made.
    """
    if not expense_id:
        raise ValueError("expense id is empty")

    logger = activity.logger
    http_client = get_http_client()

    # Get workflow info to register with the UI system
    activity_info = activity.info()
    workflow_id = activity_info.workflow_id

    # Register the workflow ID with the UI system so it can send signals
    try:
        response = await http_client.post(
            f"{EXPENSE_SERVER_HOST_PORT}/registerWorkflow",
            params={"id": expense_id},
            data={"workflow_id": workflow_id},
        )
        response.raise_for_status()
        logger.info(f"Registered expense for decision. ExpenseID: {expense_id}")
    except Exception as e:
        logger.error(f"Failed to register workflow with UI system: {e}")
        raise


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
            "stage": "start",
        },
    )

    if not expense_id:
        activity.logger.error(
            f"🚨 PAYMENT_ERROR: Empty expense ID",
            extra={
                "expense_id": expense_id,
                "activity": "payment_activity",
                "stage": "validation_error",
                "error": "expense id is empty",
            },
        )
        raise ValueError("expense id is empty")

    client = get_http_client()
    try:
        response = await client.post(
            f"{EXPENSE_SERVER_HOST_PORT}/action",
            data={"is_api_call": "true", "type": "payment", "id": expense_id},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if 400 <= e.response.status_code < 500:
            raise ApplicationError(
                f"Client error: {e.response.status_code} {e.response.text}",
                non_retryable=True,
            ) from e
        raise

    body = response.text

    activity.logger.info(
        f"📨 HTTP_RESPONSE: Received payment response from expense server",
        extra={
            "expense_id": expense_id,
            "activity": "payment_activity",
            "stage": "http_response",
            "response_text": body,
            "status_code": response.status_code,
        },
    )

    if body == "SUCCEED":
        activity.logger.info(
            f"✅ PAYMENT_SUCCESS: Payment processed successfully",
            extra={
                "expense_id": expense_id,
                "activity": "payment_activity",
                "stage": "success",
            },
        )
        return

    activity.logger.error(
        f"🚨 PAYMENT_FAILURE: Payment processing failed",
        extra={
            "expense_id": expense_id,
            "activity": "payment_activity",
            "stage": "failure",
            "response_text": body,
        },
    )
    raise Exception(body)

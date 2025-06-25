import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional

import uvicorn
from fastapi import Body, FastAPI, Form, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from temporalio.client import Client

from openai_agents_expense.models import ExpenseProcessingData, ExpenseStatusType

# Set up logging
logger = logging.getLogger(__name__)

# Use the constant from this package
EXPENSE_SERVER_HOST = "localhost"
EXPENSE_SERVER_PORT = 8099
EXPENSE_SERVER_HOST_PORT = f"http://{EXPENSE_SERVER_HOST}:{EXPENSE_SERVER_PORT}"


RESPONSE_SUCCESS = PlainTextResponse("SUCCEED")
RESPONSE_ERROR_ID_ALREADY_EXISTS = PlainTextResponse("ERROR:ID_ALREADY_EXISTS")
RESPONSE_ERROR_INVALID_ID = PlainTextResponse("ERROR:INVALID_ID")
RESPONSE_ERROR_INVALID_TYPE = PlainTextResponse("ERROR:INVALID_TYPE")
RESPONSE_ERROR_INVALID_STATE = PlainTextResponse("ERROR:INVALID_STATE")
RESPONSE_ERROR_INVALID_FORM_DATA = PlainTextResponse("ERROR:INVALID_FORM_DATA")


@dataclass
class ExpenseState:
    summary: Optional[ExpenseProcessingData]
    expense_review_state: ExpenseStatusType


# Use memory store for this sample expense system
all_expenses: Dict[str, ExpenseState] = {}
token_map: Dict[str, bytes] = {}

app = FastAPI()

# Global client - will be initialized when starting the server
workflow_client: Optional[Client] = None


@app.get("/", response_class=HTMLResponse)
@app.get("/list", response_class=HTMLResponse)
async def list_handler():
    html = """
    <h1>OpenAI Agents Expense System</h1>
    <a href="/list">HOME</a>
    <h3>All expense requests (AI + Human Review):</h3>
    <table border=1>
        <tr><th>Expense ID</th><th>Status</th><th>Action</th><th>Summary</th></tr>
    """

    # Sort keys for consistent display
    for expense_id in sorted(all_expenses.keys()):
        state = all_expenses[expense_id]
        action_link = ""
        if state.expense_review_state == "manager_review":
            action_link = f"""
                <a href="/action?type=approve&id={expense_id}">
                    <button style="background-color:#4CAF50;">APPROVE</button>
                </a>
                &nbsp;&nbsp;
                <a href="/action?type=reject&id={expense_id}">
                    <button style="background-color:#f44336;">REJECT</button>
                </a>
            """
        summary = state.summary.model_dump_json() if state.summary else "Pending"
        html += f"<tr><td>{expense_id}</td><td>{state.expense_review_state}</td><td>{action_link}</td><td>{summary}</td></tr>"

    html += "</table>"
    html += """
    <hr>
    <h4>About This System:</h4>
    <p>This expense system integrates AI agents for automated processing with human oversight.</p>
    <p>• Most expenses are processed automatically by AI agents</p>  
    <p>• Complex or high-risk expenses are escalated for human review</p>
    <p>• Use the buttons above to manually approve/reject expenses that require human decision</p>
    """
    return html


@app.post("/payment/{id}")
async def payment_handler(id: str):
    if id not in all_expenses:
        return RESPONSE_ERROR_INVALID_ID

    all_expenses[id].expense_review_state = "paid"
    logger.info(f"Payment received for {id}")
    return RESPONSE_SUCCESS


@app.get("/action", response_class=HTMLResponse)
async def action_handler(
    type: str = Query(...), id: str = Query(...), is_api_call: str = Query("false")
):
    if id not in all_expenses:
        return RESPONSE_ERROR_INVALID_ID

    starting_state = all_expenses[id].expense_review_state

    updated_state: ExpenseStatusType
    if type == "approve":
        updated_state = "approved"
    elif type == "reject":
        updated_state = "final_rejection"
    else:
        return RESPONSE_ERROR_INVALID_TYPE

    all_expenses[id].expense_review_state = updated_state

    if is_api_call == "true" or type == "payment":
        # For API calls, just return success
        if starting_state == "manager_review" and updated_state in [
            "approved",
            "final_rejection",
        ]:
            # Report state change
            await notify_expense_state_change(id, updated_state)

        print(f"Set state for {id} from {starting_state} to {updated_state}")
        return RESPONSE_SUCCESS
    else:
        # For UI calls, notify and redirect to list
        if starting_state == "manager_review" and updated_state in [
            "approved",
            "final_rejection",
        ]:
            await notify_expense_state_change(id, updated_state)

        print(f"Set state for {id} from {starting_state} to {updated_state}")
        return await list_handler()


@app.post("/create/{id}")
async def create_handler(id: str):
    if id in all_expenses:
        return RESPONSE_ERROR_ID_ALREADY_EXISTS

    # Create new ExpenseState object
    all_expenses[id] = ExpenseState(summary=None, expense_review_state="uninitialized")

    return RESPONSE_SUCCESS


@app.post("/update/{id}")
async def update_handler(id: str, expense_data: ExpenseProcessingData = Body(...)):
    if id not in all_expenses:
        return RESPONSE_ERROR_INVALID_ID

    all_expenses[id].summary = expense_data
    all_expenses[id].expense_review_state = expense_data.expense_status
    print(f"Updated state for {id} to {expense_data.expense_status}")
    return RESPONSE_SUCCESS


@app.get("/status")
async def status_handler(id: str = Query(...)):
    if id not in all_expenses:
        return RESPONSE_ERROR_INVALID_ID

    state = all_expenses[id]
    print(f"Checking status for {id}: {state}")
    return PlainTextResponse(state.expense_review_state)


@app.post("/request_review/{id}")
async def review_handler(id: str, task_token: str = Form(...)):
    if id not in all_expenses:
        return RESPONSE_ERROR_INVALID_ID

    # Convert hex string back to bytes
    try:
        task_token_bytes = bytes.fromhex(task_token)
    except ValueError:
        return RESPONSE_ERROR_INVALID_FORM_DATA

    curr_state = all_expenses[id].expense_review_state
    if curr_state != "manager_review":
        return RESPONSE_ERROR_INVALID_STATE

    print(f"Review requested for ID={id}, token={task_token}")
    token_map[id] = task_token_bytes
    return RESPONSE_SUCCESS


async def notify_expense_state_change(expense_id: str, state: ExpenseStatusType):
    if expense_id not in token_map:
        print(f"Invalid id: {expense_id}")
        return

    if workflow_client is None:
        print("Workflow client not initialized")
        return

    token = token_map[expense_id]
    try:
        handle = workflow_client.get_async_activity_handle(task_token=token)
        await handle.complete(state)
        print(f"Successfully complete activity: {token.hex()}")
    except Exception as err:
        print(f"Failed to complete activity with error: {err}")


async def main():
    global workflow_client

    # Initialize the workflow client
    workflow_client = await Client.connect("localhost:7233")

    print(
        f"OpenAI Agents Expense UI available at http://{EXPENSE_SERVER_HOST}:{EXPENSE_SERVER_PORT}"
    )

    # Start the FastAPI server
    config = uvicorn.Config(
        app, host="0.0.0.0", port=EXPENSE_SERVER_PORT, log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())

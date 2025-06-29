import asyncio
from enum import Enum
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from temporalio.client import Client

from expense import EXPENSE_SERVER_HOST, EXPENSE_SERVER_PORT


class ExpenseState(str, Enum):
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


# Use memory store for this sample expense system
all_expenses: Dict[str, ExpenseState] = {}
workflow_map: Dict[str, str] = {}  # Maps expense_id to workflow_id

app = FastAPI()

# Global client - will be initialized when starting the server
workflow_client: Optional[Client] = None


@app.get("/", response_class=HTMLResponse)
@app.get("/list", response_class=HTMLResponse)
async def list_handler():
    html = """
    <h1>SAMPLE EXPENSE SYSTEM</h1>
    <a href="/list">HOME</a>
    <h3>All expense requests:</h3>
    <table border=1>
        <tr><th>Expense ID</th><th>Status</th><th>Action</th></tr>
    """

    # Sort keys for consistent display
    for expense_id in sorted(all_expenses.keys()):
        state = all_expenses[expense_id]
        action_link = ""
        if state == ExpenseState.CREATED:
            action_link = f"""
                <a href="/action?type=approve&id={expense_id}">
                    <button style="background-color:#4CAF50;">APPROVE</button>
                </a>
                &nbsp;&nbsp;
                <a href="/action?type=reject&id={expense_id}">
                    <button style="background-color:#f44336;">REJECT</button>
                </a>
            """
        html += f"<tr><td>{expense_id}</td><td>{state}</td><td>{action_link}</td></tr>"

    html += "</table>"
    return html


@app.get("/action", response_class=HTMLResponse)
async def action_handler(
    type: str = Query(...), id: str = Query(...), is_api_call: str = Query("false")
):
    if id not in all_expenses:
        if is_api_call == "true":
            return PlainTextResponse("ERROR:INVALID_ID")
        else:
            return PlainTextResponse("Invalid ID")

    old_state = all_expenses[id]

    if type == "approve":
        all_expenses[id] = ExpenseState.APPROVED
    elif type == "reject":
        all_expenses[id] = ExpenseState.REJECTED
    elif type == "payment":
        all_expenses[id] = ExpenseState.COMPLETED
    else:
        if is_api_call == "true":
            return PlainTextResponse("ERROR:INVALID_TYPE")
        else:
            return PlainTextResponse("Invalid action type")

    if is_api_call == "true" or type == "payment":
        # For API calls and payment, just return success
        if old_state == ExpenseState.CREATED and all_expenses[id] in [
            ExpenseState.APPROVED,
            ExpenseState.REJECTED,
        ]:
            # Report state change
            await notify_expense_state_change(id, all_expenses[id])

        print(f"Set state for {id} from {old_state} to {all_expenses[id]}")
        return PlainTextResponse("SUCCEED")
    else:
        # For UI calls, notify and redirect to list
        if old_state == ExpenseState.CREATED and all_expenses[id] in [
            ExpenseState.APPROVED,
            ExpenseState.REJECTED,
        ]:
            await notify_expense_state_change(id, all_expenses[id])

        print(f"Set state for {id} from {old_state} to {all_expenses[id]}")
        return await list_handler()


@app.get("/create")
async def create_handler(id: str = Query(...), is_api_call: str = Query("false")):
    if id in all_expenses:
        if is_api_call == "true":
            return PlainTextResponse("ERROR:ID_ALREADY_EXISTS")
        else:
            return PlainTextResponse("ID already exists")

    all_expenses[id] = ExpenseState.CREATED

    if is_api_call == "true":
        print(f"Created new expense id: {id}")
        return PlainTextResponse("SUCCEED")
    else:
        print(f"Created new expense id: {id}")
        return await list_handler()


@app.get("/status")
async def status_handler(id: str = Query(...)):
    if id not in all_expenses:
        return PlainTextResponse("ERROR:INVALID_ID")

    state = all_expenses[id]
    print(f"Checking status for {id}: {state}")
    return PlainTextResponse(state.value)


@app.post("/registerWorkflow")
async def register_workflow_handler(id: str = Query(...), workflow_id: str = Form(...)):
    if id not in all_expenses:
        return PlainTextResponse("ERROR:INVALID_ID")

    curr_state = all_expenses[id]
    if curr_state != ExpenseState.CREATED:
        return PlainTextResponse("ERROR:INVALID_STATE")

    print(f"Registered workflow for ID={id}, workflow_id={workflow_id}")
    workflow_map[id] = workflow_id
    return PlainTextResponse("SUCCEED")


async def notify_expense_state_change(expense_id: str, state: str):
    if expense_id not in workflow_map:
        print(f"Invalid id: {expense_id}")
        return

    if workflow_client is None:
        print("Workflow client not initialized")
        return

    workflow_id = workflow_map[expense_id]
    try:
        # Send signal to workflow
        handle = workflow_client.get_workflow_handle(workflow_id)
        await handle.signal("expense_decision_signal", state)
        print(
            f"Successfully sent signal to workflow: {workflow_id} with decision: {state}"
        )
    except Exception as err:
        print(f"Failed to send signal to workflow with error: {err}")


async def main():
    global workflow_client

    # Initialize the workflow client
    workflow_client = await Client.connect("localhost:7233")

    print(
        f"Expense system UI available at http://{EXPENSE_SERVER_HOST}:{EXPENSE_SERVER_PORT}"
    )

    # Start the FastAPI server
    config = uvicorn.Config(
        app, host="0.0.0.0", port=EXPENSE_SERVER_PORT, log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())

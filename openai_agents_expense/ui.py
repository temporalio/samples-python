import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import uvicorn
from fastapi import Body, FastAPI, Form, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from temporalio.client import Client

from openai_agents_expense.models import ExpenseProcessingData, ExpenseStatusType

# Set up logging
logger = logging.getLogger(__name__)


def format_expense_summary(data: ExpenseProcessingData) -> str:
    """Format ExpenseProcessingData into readable HTML"""
    if not data:
        return "Pending"

    html = "<div style='font-family: monospace; font-size: 12px; max-width: 600px;'>"

    # Status
    html += f"<div><strong>Status:</strong> {data.expense_status}</div><br>"

    # Basic expense details
    if hasattr(data, "expense_report") and data.expense_report:
        exp = data.expense_report
        html += "<div><strong>Expense Details:</strong></div>"
        html += f"<div style='margin-left: 15px;'>"
        if hasattr(exp, "amount") and exp.amount:
            html += f"• Amount: ${exp.amount}<br>"
        if hasattr(exp, "description") and exp.description:
            html += f"• Description: {exp.description}<br>"
        if hasattr(exp, "vendor") and exp.vendor:
            html += f"• Vendor: {exp.vendor}<br>"
        if hasattr(exp, "expense_date") and exp.expense_date:
            html += f"• Date: {exp.expense_date}<br>"
        if hasattr(exp, "department") and exp.department:
            html += f"• Department: {exp.department}<br>"
        if hasattr(exp, "employee_id") and exp.employee_id:
            html += f"• Employee: {exp.employee_id}<br>"
        html += "</div><br>"

    # Categorization
    if hasattr(data, "categorization") and data.categorization:
        cat = data.categorization
        html += "<div><strong>Categorization:</strong></div>"
        html += f"<div style='margin-left: 15px;'>"
        if hasattr(cat, "category") and cat.category:
            html += f"• Category: {cat.category}<br>"
        if hasattr(cat, "confidence") and cat.confidence:
            html += f"• Confidence: {cat.confidence:.0%}<br>"
        if hasattr(cat, "reasoning") and cat.reasoning:
            reasoning = (
                cat.reasoning[:200] + "..."
                if len(cat.reasoning) > 200
                else cat.reasoning
            )
            html += f"• Reasoning: {reasoning}<br>"
        html += "</div><br>"

    # Policy evaluation
    if hasattr(data, "policy_evaluation") and data.policy_evaluation:
        policy = data.policy_evaluation
        html += "<div><strong>Policy Evaluation:</strong></div>"
        html += f"<div style='margin-left: 15px;'>"
        if hasattr(policy, "compliant") and policy.compliant is not None:
            compliant_text = "✅ Compliant" if policy.compliant else "❌ Non-compliant"
            html += f"• Status: {compliant_text}<br>"
        if (
            hasattr(policy, "requires_human_review")
            and policy.requires_human_review is not None
        ):
            review_text = "Yes" if policy.requires_human_review else "No"
            html += f"• Requires Review: {review_text}<br>"
        if hasattr(policy, "violations") and policy.violations:
            violations_text = ", ".join(str(v) for v in policy.violations)
            html += f"• Violations: {violations_text}<br>"
        html += "</div><br>"

    # Fraud assessment
    if hasattr(data, "fraud_assessment") and data.fraud_assessment:
        fraud = data.fraud_assessment
        html += "<div><strong>Fraud Assessment:</strong></div>"
        html += f"<div style='margin-left: 15px;'>"
        if hasattr(fraud, "overall_risk") and fraud.overall_risk:
            risk_color = {"low": "green", "medium": "orange", "high": "red"}.get(
                fraud.overall_risk.lower(), "black"
            )
            html += f"• Risk Level: <span style='color: {risk_color};'>{fraud.overall_risk.upper()}</span><br>"
        if hasattr(fraud, "flags") and fraud.flags:
            flags_text = (
                ", ".join(str(f) for f in fraud.flags) if fraud.flags else "None"
            )
            html += f"• Flags: {flags_text}<br>"
        if hasattr(fraud, "vendor_risk_indicators") and fraud.vendor_risk_indicators:
            indicators_text = ", ".join(str(i) for i in fraud.vendor_risk_indicators)
            html += f"• Vendor Risk Indicators: {indicators_text}<br>"
        html += "</div><br>"

    # Agent decision
    if hasattr(data, "agent_decision") and data.agent_decision:
        decision = data.agent_decision
        html += "<div><strong>Agent Decision:</strong></div>"
        html += f"<div style='margin-left: 15px;'>"
        if hasattr(decision, "decision") and decision.decision:
            decision_color = {
                "approved": "green",
                "rejected": "red",
                "escalated": "orange",
            }.get(decision.decision.lower(), "black")
            html += f"• Decision: <span style='color: {decision_color};'>{decision.decision.upper()}</span><br>"
        if hasattr(decision, "escalation_reason") and decision.escalation_reason:
            html += f"• Escalation Reason: {decision.escalation_reason}<br>"
        if hasattr(decision, "external_reasoning") and decision.external_reasoning:
            reasoning = (
                decision.external_reasoning[:150] + "..."
                if len(decision.external_reasoning) > 150
                else decision.external_reasoning
            )
            html += f"• Reasoning: {reasoning}<br>"
        html += "</div><br>"

    # Final response summary
    if hasattr(data, "expense_response") and data.expense_response:
        response = data.expense_response
        if hasattr(response, "decision_summary") and response.decision_summary:
            summary = (
                response.decision_summary[:200] + "..."
                if len(response.decision_summary) > 200
                else response.decision_summary
            )
            html += f"<div><strong>Summary:</strong> {summary}</div>"

    html += "</div>"
    return html


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
    created_at: datetime


# Use memory store for this sample expense system
all_expenses: Dict[str, ExpenseState] = {}
token_map: Dict[str, bytes] = {}
workflow_map: Dict[str, str] = {}  # Maps expense_id to workflow_id

app = FastAPI()

# Global client - will be initialized when starting the server
workflow_client: Optional[Client] = None


@app.get("/", response_class=HTMLResponse)
@app.get("/list", response_class=HTMLResponse)
async def list_handler():
    html = """
    <html>
    <head>
        <meta http-equiv="refresh" content="1">
        <title>OpenAI Agents Expense System</title>
    </head>
    <body>
    <h1>OpenAI Agents Expense System</h1>
    <a href="/list">HOME</a>
    <h3>All expense requests (AI + Human Review):</h3>
    <table border=1 style="width: 100%; border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th style="padding: 10px; width: 200px;">Expense ID</th>
            <th style="padding: 10px; width: 150px;">Status</th>
            <th style="padding: 10px; width: 150px;">Action</th>
            <th style="padding: 10px;">Summary</th>
        </tr>
    """

    # Sort by creation time (newest first)
    sorted_expense_ids = sorted(
        all_expenses.keys(), key=lambda x: all_expenses[x].created_at, reverse=True
    )
    for expense_id in sorted_expense_ids:
        state = all_expenses[expense_id]
        action_link = ""
        if state.expense_review_state == "manager_review":
            action_link = (
                f'<form method="post" action="/action" style="display:inline;">'
                f'<input type="hidden" name="type" value="approve">'
                f'<input type="hidden" name="id" value="{expense_id}">'
                '<button type="submit" style="background-color:#4CAF50;">APPROVE</button>'
                "</form>"
                "&nbsp;&nbsp;"
                f'<form method="post" action="/action" style="display:inline;">'
                f'<input type="hidden" name="type" value="reject">'
                f'<input type="hidden" name="id" value="{expense_id}">'
                '<button type="submit" style="background-color:#f44336;">REJECT</button>'
                "</form>"
            )
        summary = format_expense_summary(state.summary) if state.summary else "Pending"
        html += f'<tr style="border-bottom: 1px solid #ddd;"><td style="padding: 10px; vertical-align: top;">{expense_id}</td><td style="padding: 10px; vertical-align: top;">{state.expense_review_state}</td><td style="padding: 10px; vertical-align: top;">{action_link}</td><td style="padding: 10px; vertical-align: top;">{summary}</td></tr>'

    html += "</table>"
    html += """
    <hr>
    <h4>About This System:</h4>
    <p>This expense system integrates AI agents for automated processing with human oversight.</p>
    <p>• Most expenses are processed automatically by AI agents</p>  
    <p>• Complex or high-risk expenses are escalated for human review</p>
    <p>• Use the buttons above to manually approve/reject expenses that require human decision</p>
    </body>
    </html>
    """
    return html


@app.post("/payment/{id}")
async def payment_handler(id: str):
    if id not in all_expenses:
        return RESPONSE_ERROR_INVALID_ID

    all_expenses[id].expense_review_state = "paid"
    logger.info(f"Payment received for {id}")
    return RESPONSE_SUCCESS


@app.post("/action")
async def action_handler(
    type: str = Form(...), id: str = Form(...), is_api_call: str = Form("false")
):
    if id not in all_expenses:
        return RESPONSE_ERROR_INVALID_ID

    starting_state = all_expenses[id].expense_review_state

    updated_state: ExpenseStatusType
    if type == "approve":
        updated_state = "approved"
    elif type == "reject":
        updated_state = "final_rejection"
    elif type == "payment":
        updated_state = "paid"
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
        return RedirectResponse(url="/list", status_code=303)


@app.post("/create/{id}")
async def create_handler(id: str):
    if id in all_expenses:
        return RESPONSE_ERROR_ID_ALREADY_EXISTS

    # Create new ExpenseState object
    all_expenses[id] = ExpenseState(
        summary=None, expense_review_state="uninitialized", created_at=datetime.now()
    )

    return RESPONSE_SUCCESS


@app.post("/registerWorkflow")
async def register_workflow_handler(id: str = Query(...), workflow_id: str = Form(...)):
    if id not in all_expenses:
        return PlainTextResponse("ERROR:INVALID_ID")

    print(f"Registered workflow for ID={id}, workflow_id={workflow_id}")
    workflow_map[id] = workflow_id
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
    if expense_id not in workflow_map:
        print(f"No workflow registered for expense ID: {expense_id}")
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

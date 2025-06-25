import asyncio
import os

from flask import Flask, jsonify, request, send_from_directory
from temporalio.client import Client
from temporalio.contrib.openai_agents.open_ai_data_converter import (
    open_ai_data_converter,
)

from openai_agents.workflows.agents_as_tools_workflow import AgentsAsToolsWorkflow
from openai_agents.workflows.customer_service_workflow import CustomerServiceWorkflow
from openai_agents.workflows.research_bot_workflow import ResearchWorkflow
from openai_agents.workflows.tools_workflow import ToolsWorkflow

app = Flask(__name__)

# Serve the HTML file
@app.route("/")
def index():
    return send_from_directory(".", "research_ui.html")


@app.route("/api/research", methods=["POST"])
def research():
    try:
        data = request.get_json()
        prompt = data.get("prompt")

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        result = asyncio.run(
            run_workflow(ResearchWorkflow.run, prompt, "research-workflow")
        )
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents-as-tools", methods=["POST"])
def agents_as_tools():
    try:
        data = request.get_json()
        prompt = data.get("prompt")

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        result = asyncio.run(
            run_workflow(AgentsAsToolsWorkflow.run, prompt, "agents-as-tools-workflow")
        )
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools", methods=["POST"])
def tools():
    try:
        data = request.get_json()
        prompt = data.get("prompt")

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        result = asyncio.run(run_workflow(ToolsWorkflow.run, prompt, "tools-workflow"))
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/customer-service", methods=["POST"])
def customer_service():
    try:
        data = request.get_json()
        prompt = data.get("prompt")

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # For customer service, we'll start a workflow and send a message
        result = asyncio.run(run_customer_service_workflow(prompt))
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


async def run_workflow(workflow_fn, prompt, workflow_prefix):
    client = await Client.connect(
        "localhost:7233",
        data_converter=open_ai_data_converter,
    )

    result = await client.execute_workflow(
        workflow_fn,
        prompt,
        id=f"{workflow_prefix}-{abs(hash(prompt))}",
        task_queue="openai-agents-task-queue",
    )

    return result


async def run_customer_service_workflow(prompt):
    from openai_agents.workflows.customer_service_workflow import (
        ProcessUserMessageInput,
    )

    client = await Client.connect(
        "localhost:7233",
        data_converter=open_ai_data_converter,
    )

    workflow_id = f"customer-service-{abs(hash(prompt))}"

    # Start the customer service workflow
    handle = await client.start_workflow(
        CustomerServiceWorkflow.run,
        id=workflow_id,
        task_queue="openai-agents-task-queue",
    )

    # Send the user message
    message_input = ProcessUserMessageInput(user_input=prompt, chat_length=0)

    new_history = await handle.execute_update(
        CustomerServiceWorkflow.process_user_message, message_input
    )

    return "\n".join(new_history) if new_history else "No response received"


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")

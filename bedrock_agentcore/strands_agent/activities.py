import os
from typing import Any

from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from strands_tools.code_interpreter.models import ExecuteCodeAction, LanguageType
from temporalio import activity


# @@@SNIPSTART python-agentcore-code-interpreter-activity
# Use AgentCore Code Interpreter to provide a code sandbox and execute LLM generated solution
@activity.defn
def execute_code(
    code: str, language: LanguageType = LanguageType.PYTHON
) -> dict[str, Any]:
    """Run code in this Sessions's sandbox (workflow ID) and return the Code Interpreter result."""
    interpreter = AgentCoreCodeInterpreter(
        region=os.environ.get("AWS_REGION", "us-west-2"),
        session_name=activity.info().workflow_id,
    )
    return interpreter.execute_code(
        ExecuteCodeAction(type="executeCode", code=code, language=language)
    )


# @@@SNIPEND

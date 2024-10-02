from dataclasses import dataclass
from enum import StrEnum

TASK_QUEUE = "my-task-queue"
WORKFLOW_ID = "my-workflow-id"


class WorkflowExitType(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    CONTINUE_AS_NEW = "continue_as_new"
    CANCELLATION = "cancellation"


@dataclass
class WorkflowInput:
    exit_type: WorkflowExitType


class OnWorkflowExitAction(StrEnum):
    CONTINUE = "continue"
    ABORT_WITH_COMPENSATION = "abort_with_compensation"


@dataclass
class UpdateInput:
    on_premature_workflow_exit: OnWorkflowExitAction

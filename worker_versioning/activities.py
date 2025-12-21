from dataclasses import dataclass

from temporalio import activity


@dataclass
class IncompatibleActivityInput:
    """Input for the incompatible activity."""

    called_by: str
    more_data: str


@activity.defn
async def some_activity(called_by: str) -> str:
    """Basic activity for the workflow."""
    return f"some_activity called by {called_by}"


@activity.defn
async def some_incompatible_activity(input_data: IncompatibleActivityInput) -> str:
    """Incompatible activity that takes different input."""
    return f"some_incompatible_activity called by {input_data.called_by} with {input_data.more_data}"

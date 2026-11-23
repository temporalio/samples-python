"""Tools for the human-in-the-loop sample.

``tool_as_activity(...)`` registers the tool in the worker process, so call it
here at module level and import this module in the workflow file under
``workflow.unsafe.imports_passed_through()``.
"""

from datetime import timedelta

from temporalio.deepagents import tool_as_activity


def book_trip(city: str) -> str:
    """Book a trip to a city (requires human approval)."""
    return f"Booked a trip to {city}."


trip_tool = tool_as_activity(book_trip, start_to_close_timeout=timedelta(seconds=30))

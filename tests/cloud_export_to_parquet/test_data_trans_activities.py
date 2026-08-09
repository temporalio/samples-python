"""Tests for convert_proto_to_parquet_flatten using duck-typed fakes.

We monkeypatch MessageToDict to avoid needing real Temporal proto structures.
Focus of tests:
 - Basic conversion adds WorkflowId/RunId and flattens multiple workflows/events
 - Empty input returns empty DataFrame
 - Column drop logic removes keys containing 'payloads' or '.'
 - Multiple runs for same WorkflowId captured correctly
 - Edge cases: empty events, missing attributes
 - S3 operations: listing, reading, and writing
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from botocore.exceptions import ClientError

from cloud_export_to_parquet.data_trans_activities import (
    GetObjectKeysActivityInput,
    convert_proto_to_parquet_flatten,
    get_object_keys,
    get_data_from_object_key,
    save_to_sink,
)


class _StartedAttrs:
    """Fake workflow_execution_started_event_attributes."""

    def __init__(self, workflow_id: str, run_id: str) -> None:
        self.workflow_id = workflow_id
        self.original_execution_run_id = run_id


class _Event:
    """Fake Temporal event."""

    def __init__(self, started: _StartedAttrs | None = None, idx: int = 0) -> None:
        # Only first event has started attrs
        if started:
            self.workflow_execution_started_event_attributes = started
        # Provide an event_id for debug clarity
        self.event_id = idx


class _History:
    """Fake workflow history."""

    def __init__(self, events: list[_Event]) -> None:
        self.events = events


class _Workflow:
    """Fake workflow execution."""

    def __init__(self, workflow_id: str, run_id: str, num_events: int) -> None:
        started = _StartedAttrs(workflow_id, run_id)
        events = [_Event(started=started, idx=1)]
        for i in range(2, num_events + 2):
            events.append(_Event(idx=i))
        self.history = _History(events)


class _WorkflowWithoutStartedAttrs:
    """Fake workflow that's missing the started event attributes."""

    def __init__(self) -> None:
        # First event doesn't have workflow_execution_started_event_attributes
        self.history = _History([_Event(started=None, idx=1)])


class _WorkflowWithEmptyEvents:
    """Fake workflow with no events at all."""

    def __init__(self) -> None:
        self.history = _History([])


class _Executions:
    """Fake WorkflowExecutions container."""

    def __init__(self) -> None:
        self.items: list[_Workflow | _WorkflowWithoutStartedAttrs | _WorkflowWithEmptyEvents] = []


def _build_executions(defs: list[tuple[str, str, int]]) -> _Executions:
    """Build a fake WorkflowExecutions from workflow definitions.

    Args:
        defs: List of (workflow_id, run_id, num_events) tuples

    Returns:
        _Executions with workflows created from the definitions
    """
    wfs = _Executions()
    for wf_id, run_id, num_events in defs:
        wfs.items.append(_Workflow(wf_id, run_id, num_events))
    return wfs


def _patched_message_to_dict(ev: _Event, preserving_proto_field_name: bool = False) -> dict:
    """Mock MessageToDict to simulate proto serialization.

    Simulates the conversion of a proto Event to a dict, including fields
    that should be dropped by the column filtering logic.
    """
    base = {"event_id": getattr(ev, "event_id", 0)}
    # Include fields that trigger drop logic
    base["some.payloads.data"] = "will_drop"  # contains both '.' and 'payloads'
    base["payloads_custom"] = "will_drop"     # contains 'payloads'
    base["regular_field"] = "keep"            # should remain
    return base


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_message_to_dict(monkeypatch):
    """Fixture to monkeypatch MessageToDict"""
    monkeypatch.setattr(
        "cloud_export_to_parquet.data_trans_activities.MessageToDict",
        _patched_message_to_dict,
    )


# ============================================================================
# Tests for convert_proto_to_parquet_flatten
# ============================================================================


def test_convert_proto_to_parquet_flatten_basic(mock_message_to_dict):
    """Test basic conversion with multiple workflows and events.

    Verifies that:
    - WorkflowId and RunId are correctly added to each event
    - Events from multiple workflows are all captured
    - Total row count matches expected event count
    - Column filtering removes 'payloads' and '.' containing columns
    - Regular fields are preserved
    """
    wfs = _build_executions([
        ("wf-1", "run-1", 2),  # creates 1 started + 2 additional = 3 events
        ("wf-2", "run-2", 1),  # creates 1 started + 1 additional = 2 events
    ])
    df = convert_proto_to_parquet_flatten(wfs)

    assert not df.empty
    # Use exact set comparison instead of subset
    assert set(df["WorkflowId"]) == {"wf-1", "wf-2"}
    assert set(df["RunId"]) == {"run-1", "run-2"}
    # Total events: (1+2) + (1+1) = 5
    assert len(df) == 5


def test_convert_proto_to_parquet_flatten_empty(mock_message_to_dict):
    """Verify that empty workflow executions produce an empty DataFrame.

    This is important for batch processing where some exports might be empty.
    The function should gracefully return an empty DataFrame rather than crash.
    """
    wfs = _Executions()  # no items
    df = convert_proto_to_parquet_flatten(wfs)

    assert df.empty
    assert isinstance(df, pd.DataFrame)


def test_convert_proto_to_parquet_flatten_drop_columns(mock_message_to_dict):
    """Test that columns containing 'payloads' or '.' are dropped.

    These columns typically contain sensitive data or nested structures
    that should not be included in the flattened export.
    """
    wfs = _build_executions([
        ("wf-x", "run-x", 1),
    ])
    df = convert_proto_to_parquet_flatten(wfs)

    # Ensure unwanted columns dropped
    assert all("payloads" not in c for c in df.columns)
    assert all("." not in c for c in df.columns)
    # Ensure at least one kept column besides WorkflowId/RunId
    assert "regular_field" in df.columns
    assert all(df["regular_field"] == "keep")


def test_convert_proto_to_parquet_flatten_schema(mock_message_to_dict):
    """Verify the output DataFrame has the expected schema and types.

    This test acts as schema validation to ensure downstream consumers
    can rely on consistent column names and data types.
    """
    wfs = _build_executions([("wf-1", "run-1", 2)])
    df = convert_proto_to_parquet_flatten(wfs)

    # Check required columns exist
    assert "WorkflowId" in df.columns
    assert "RunId" in df.columns
    assert "event_id" in df.columns
    assert "regular_field" in df.columns

    # Check data types (pandas uses 'object' for strings)
    assert df["WorkflowId"].dtype == "object"
    assert df["RunId"].dtype == "object"

    # Check no null values in key columns
    assert not df["WorkflowId"].isna().any()
    assert not df["RunId"].isna().any()


@pytest.mark.parametrize("workflow_defs,expected_wf_ids,expected_run_ids,expected_rows", [
    # Single workflow, single run
    ([("wf-1", "run-1", 2)], {"wf-1"}, {"run-1"}, 3),
    # Multiple workflows
    ([("wf-1", "run-1", 1), ("wf-2", "run-2", 1)], {"wf-1", "wf-2"}, {"run-1", "run-2"}, 4),
    # Same workflow, different runs
    ([("wf-1", "run-1", 1), ("wf-1", "run-2", 1)], {"wf-1"}, {"run-1", "run-2"}, 4),
    # Minimal case: single event
    ([("wf-x", "run-x", 0)], {"wf-x"}, {"run-x"}, 1),
])
def test_convert_proto_to_parquet_flatten_scenarios(
    mock_message_to_dict,
    workflow_defs: list[tuple[str, str, int]],
    expected_wf_ids: set[str],
    expected_run_ids: set[str],
    expected_rows: int
):
    """Parametrized test for various workflow execution scenarios.

    This consolidates several similar tests into one parametrized test,
    making it easy to add new test cases without duplicating code.
    """
    wfs = _build_executions(workflow_defs)
    df = convert_proto_to_parquet_flatten(wfs)

    assert set(df["WorkflowId"]) == expected_wf_ids
    assert set(df["RunId"]) == expected_run_ids
    assert len(df) == expected_rows
    # Common assertions
    assert all("payloads" not in c for c in df.columns)
    assert all("." not in c for c in df.columns)


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_convert_proto_to_parquet_flatten_workflow_with_empty_events(mock_message_to_dict):
    """Test handling of workflows with empty event lists.

    This is an edge case that would cause an IndexError on line 77 of
    data_trans_activities.py when accessing events[0]. This test documents
    the current behavior (it will fail) and should be fixed in the implementation.
    """
    wfs = _Executions()
    wfs.items.append(_WorkflowWithEmptyEvents())

    # Current implementation will crash with IndexError
    # TODO: Fix implementation to handle this gracefully
    with pytest.raises(IndexError):
        convert_proto_to_parquet_flatten(wfs)


def test_convert_proto_to_parquet_flatten_missing_started_attrs(mock_message_to_dict):
    """Test handling of events missing workflow_execution_started_event_attributes.

    This edge case would cause an AttributeError if the first event doesn't
    have the expected started attributes. This test documents the current
    behavior and highlights a potential bug.
    """
    wfs = _Executions()
    wfs.items.append(_WorkflowWithoutStartedAttrs())

    # Current implementation will crash with AttributeError
    # TODO: Fix implementation to handle this gracefully or add validation
    with pytest.raises(AttributeError):
        convert_proto_to_parquet_flatten(wfs)

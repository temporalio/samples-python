"""Verify a ticket-triage trace in Arize Phoenix through its REST API.

Fetches every span of the trace, rebuilds the tree, and deep-compares it
against the expected shape — including OpenInference span kinds — then checks
that Temporal spans carry the enrichment attributes, that every LLM span has a
model and token usage, and that no span was duplicated (running the worker
with --replay-stress surfaces replay-caused duplicates here, if there were
any).

Usage:
    python -m arize_tracing.verify_trace --trace-id <hex trace id>
    python -m arize_tracing.verify_trace --workflow-id <workflow id>
    python -m arize_tracing.verify_trace --trace-id <id> --expect declined
    python -m arize_tracing.verify_trace --trace-id <id> --expect-attempts classify_ticket=2
    python -m arize_tracing.verify_trace --workflow-id <id> --expect-runs 2
    python -m arize_tracing.verify_trace --trace-id <id> --scenario agents

Stdlib-only on purpose so it is trivially copy-out-able. Reads the same
environment variables as the samples: PHOENIX_COLLECTOR_ENDPOINT,
PHOENIX_API_KEY, and ARIZE_PROJECT_NAME / PHOENIX_PROJECT_NAME.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

DEFAULT_PHOENIX_ENDPOINT = "http://localhost:6006"
DEFAULT_PROJECT_NAME = "temporal-ticket-triage"

TEMPORAL_SPAN_PREFIXES = (
    "StartWorkflow:",
    "RunWorkflow:",
    "StartActivity:",
    "RunActivity:",
    "StartWorkflowUpdate:",
    "ValidateUpdate:",
    "HandleUpdate:",
    "HandleSignal:",
    "HandleQuery:",
    "StartChildWorkflow:",
    "SignalWorkflow:",
    "QueryWorkflow:",
)

# Expected span trees as (depth, name, kind) rows; siblings sorted by name,
# then by start time. LLM spans are normalized to "<llm>" (their name depends
# on the API used, for example "ChatCompletion"); their kind must be LLM.
EXPECTED_APPROVED = [
    (0, "ticket-triage", "CHAIN"),
    (1, "StartWorkflow:TicketTriageWorkflow", "CHAIN"),
    (2, "RunWorkflow:TicketTriageWorkflow", "CHAIN"),
    (3, "StartActivity:draft_reply", "CHAIN"),
    (4, "RunActivity:draft_reply", "CHAIN"),
    (5, "<llm>", "LLM"),
    (3, "triage", "CHAIN"),
    (4, "StartActivity:classify_ticket", "CHAIN"),
    (5, "RunActivity:classify_ticket", "CHAIN"),
    (6, "<llm>", "LLM"),
    (4, "StartActivity:lookup_account", "CHAIN"),
    (5, "RunActivity:lookup_account", "CHAIN"),
    (1, "StartWorkflowUpdate:approve", "CHAIN"),
    (2, "HandleUpdate:approve", "CHAIN"),
    (2, "ValidateUpdate:approve", "CHAIN"),
]
# The declined path never reaches draft_reply: drop its three rows explicitly.
EXPECTED_DECLINED = [
    (0, "ticket-triage", "CHAIN"),
    (1, "StartWorkflow:TicketTriageWorkflow", "CHAIN"),
    (2, "RunWorkflow:TicketTriageWorkflow", "CHAIN"),
    (3, "triage", "CHAIN"),
    (4, "StartActivity:classify_ticket", "CHAIN"),
    (5, "RunActivity:classify_ticket", "CHAIN"),
    (6, "<llm>", "LLM"),
    (4, "StartActivity:lookup_account", "CHAIN"),
    (5, "RunActivity:lookup_account", "CHAIN"),
    (1, "StartWorkflowUpdate:approve", "CHAIN"),
    (2, "HandleUpdate:approve", "CHAIN"),
    (2, "ValidateUpdate:approve", "CHAIN"),
]


def _base_url() -> str:
    return os.environ.get(
        "PHOENIX_COLLECTOR_ENDPOINT", DEFAULT_PHOENIX_ENDPOINT
    ).rstrip("/")


def _project() -> str:
    return (
        os.environ.get("ARIZE_PROJECT_NAME")
        or os.environ.get("PHOENIX_PROJECT_NAME")
        or DEFAULT_PROJECT_NAME
    )


def _api_get(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    url = f"{_base_url()}/v1{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    headers = {}
    api_key = os.environ.get("PHOENIX_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def _spans(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Page through GET /v1/projects/{project}/spans with the given filters."""
    project = urllib.parse.quote(_project(), safe="")
    spans: list[dict[str, Any]] = []
    cursor: Optional[str] = None
    while True:
        query = dict(params, limit=100)
        if cursor:
            query["cursor"] = cursor
        page = _api_get(f"/projects/{project}/spans", query)
        spans.extend(page.get("data") or [])
        cursor = page.get("next_cursor")
        if not cursor:
            return spans


def _flatten(attributes: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    # Phoenix returns attributes with dotted keys; nested dicts are flattened
    # defensively so both shapes read the same.
    flat: dict[str, Any] = {}
    for key, value in attributes.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, f"{name}."))
        else:
            flat[name] = value
    return flat


def _attrs(span: dict[str, Any]) -> dict[str, Any]:
    return _flatten(span.get("attributes") or {})


def _trace_ids_for_workflow(workflow_id: str, scenario: str) -> list[str]:
    """Trace IDs whose RunWorkflow span belongs to the workflow, newest first."""
    name = (
        "RunWorkflow:TicketTriageWorkflow"
        if scenario == "ticket-triage"
        else "temporal:executeWorkflow"
    )
    spans = _spans({"attribute": f"temporalWorkflowID:{workflow_id}", "name": name})
    if not spans:
        spans = _spans({"attribute": f"session.id:{workflow_id}", "parent_id": "null"})
    spans.sort(key=lambda s: s["start_time"], reverse=True)
    trace_ids: list[str] = []
    for span in spans:
        trace_id = span["context"]["trace_id"]
        if trace_id not in trace_ids:
            trace_ids.append(trace_id)
    return trace_ids


def _poll_stable_trace(trace_id: str, timeout_seconds: int) -> list[dict[str, Any]]:
    """Poll until the trace exists and its span count is stable.

    Phoenix ingestion is asynchronous, so a freshly finished run may land
    over a few seconds even though export already succeeded.
    """
    deadline = time.monotonic() + timeout_seconds
    previous_count = -1
    while time.monotonic() < deadline:
        spans = _spans({"trace_id": trace_id})
        if spans and len(spans) == previous_count:
            return spans
        previous_count = len(spans)
        time.sleep(2)
    raise SystemExit(
        f"FAIL: trace {trace_id} not fully ingested within {timeout_seconds}s"
    )


def _normalized_name(span: dict[str, Any]) -> str:
    return "<llm>" if span.get("span_kind") == "LLM" else str(span["name"])


def _build_tree(spans: list[dict[str, Any]]) -> list[tuple[int, str, str]]:
    by_id = {s["context"]["span_id"]: s for s in spans}
    children: dict[Optional[str], list[dict[str, Any]]] = {}
    for span in spans:
        parent = span.get("parent_id")
        children.setdefault(parent if parent in by_id else None, []).append(span)
    rows: list[tuple[int, str, str]] = []

    def walk(span: dict[str, Any], depth: int) -> None:
        rows.append((depth, _normalized_name(span), str(span.get("span_kind"))))
        for child in sorted(
            children.get(span["context"]["span_id"], []),
            key=lambda s: (_normalized_name(s), s["start_time"]),
        ):
            walk(child, depth + 1)

    for root in sorted(
        children.get(None, []), key=lambda s: (str(s["name"]), s["start_time"])
    ):
        walk(root, 0)
    return rows


def _print_tree(rows: list[tuple[int, str, str]]) -> None:
    for depth, name, kind in rows:
        print(f"    {'    ' * depth}{name}  [{kind}]")


def _expected_tree(expect: str, attempts: dict[str, int]) -> list[tuple[int, str, str]]:
    rows = list(EXPECTED_DECLINED if expect == "declined" else EXPECTED_APPROVED)
    for activity_name, count in attempts.items():
        # Failed attempts have no LLM child; they precede the successful one.
        index = rows.index(
            next(row for row in rows if row[1] == f"RunActivity:{activity_name}")
        )
        depth = rows[index][0]
        rows[index:index] = [(depth, f"RunActivity:{activity_name}", "CHAIN")] * (
            count - 1
        )
    return rows


def _trace_url(trace_id: str) -> str:
    try:
        projects = _api_get("/projects").get("data") or []
        for project in projects:
            if project.get("name") == _project():
                return f"{_base_url()}/projects/{project['id']}/traces/{trace_id}"
    except (OSError, ValueError):
        pass
    return f"{_base_url()}/projects"


def _verify_common(
    trace_id: str,
    spans: list[dict[str, Any]],
    failures: list[str],
    args: argparse.Namespace,
) -> None:
    # No duplicate spans (workflow replay must never re-emit spans).
    all_ids = [s["context"]["span_id"] for s in spans]
    if len(set(all_ids)) != len(all_ids):
        failures.append("duplicate span ids present")

    # Every child points at a span that is part of the trace. A missing parent
    # means a span was exported with the wrong parent, which Arize renders as a
    # detached subtree.
    span_ids = {s["context"]["span_id"] for s in spans}
    orphans = [
        s for s in spans if s.get("parent_id") and s["parent_id"] not in span_ids
    ]
    if orphans:
        names = sorted({s["name"] for s in orphans})
        failures.append(
            f"{len(orphans)} span(s) reference a parent that is not in the trace: {names}"
        )

    # The root carries the OpenInference trace-level attributes.
    roots = [s for s in spans if not s.get("parent_id")]
    if len(roots) != 1:
        failures.append(f"expected exactly one root span, found {len(roots)}")
    else:
        root_attrs = _attrs(roots[0])
        for key in ("session.id", "user.id", "input.value", "output.value"):
            if not root_attrs.get(key):
                failures.append(f"root span missing {key}")
        if args.workflow_id and root_attrs.get("session.id") != args.workflow_id:
            failures.append("root span session.id is not the workflow id")

    # Every LLM span has a model and token usage.
    for span in spans:
        if span.get("span_kind") != "LLM":
            continue
        attrs = _attrs(span)
        if not attrs.get("llm.model_name"):
            failures.append(
                f"LLM span {span['context']['span_id']} missing llm.model_name"
            )
        if (
            attrs.get("llm.token_count.prompt") is None
            or attrs.get("llm.token_count.completion") is None
        ):
            failures.append(
                f"LLM span {span['context']['span_id']} missing token counts"
            )


def _verify_ticket_triage(
    args: argparse.Namespace, trace_id: str, spans: list[dict[str, Any]]
) -> list[str]:
    failures: list[str] = []
    _verify_common(trace_id, spans, failures, args)

    actual = _build_tree(spans)
    print(f"Trace {trace_id}: {len(spans)} spans")
    _print_tree(actual)

    run_workflow_spans = [s for s in spans if s["name"].startswith("RunWorkflow:")]
    if args.expect_runs == 1:
        expected = _expected_tree(args.expect, args.expect_attempts)
        if actual != expected:
            failures.append("tree mismatch")
            print("  Expected:")
            _print_tree(expected)
    else:
        # Reset / retry experiments: several runs share one trace.
        run_ids = {_attrs(s).get("temporalRunID") for s in run_workflow_spans}
        if (
            len(run_workflow_spans) != args.expect_runs
            or len(run_ids) != args.expect_runs
        ):
            failures.append(
                f"expected {args.expect_runs} RunWorkflow spans with distinct run ids, "
                f"found {len(run_workflow_spans)} ({len(run_ids)} run ids)"
            )
    if args.expect_runs == 1 and len(run_workflow_spans) != 1:
        failures.append(
            f"expected exactly one RunWorkflow span, found {len(run_workflow_spans)}"
        )

    # Temporal spans carry the OpenInference enrichment.
    for span in spans:
        if not span["name"].startswith(TEMPORAL_SPAN_PREFIXES):
            continue
        attrs = _attrs(span)
        if span.get("span_kind") != "CHAIN":
            failures.append(
                f"{span['name']} has kind {span.get('span_kind')}, expected CHAIN"
            )
        if not attrs.get("session.id"):
            failures.append(f"{span['name']} missing session.id")
        if not attrs.get("metadata.temporalWorkflowID"):
            failures.append(f"{span['name']} missing metadata.temporalWorkflowID")

    # Activity attempts: one RunActivity span per attempt, failed ones first.
    for activity_name, count in args.expect_attempts.items():
        runs = sorted(
            (s for s in spans if s["name"] == f"RunActivity:{activity_name}"),
            key=lambda s: s["start_time"],
        )
        starts = [s for s in spans if s["name"] == f"StartActivity:{activity_name}"]
        if len(runs) != count:
            failures.append(
                f"expected {count} RunActivity:{activity_name} spans, found {len(runs)}"
            )
            continue
        if len(starts) != 1:
            failures.append(
                f"expected one StartActivity:{activity_name} span, found {len(starts)}"
            )
        attempts = [_attrs(s).get("temporal.activity.attempt") for s in runs]
        if attempts != list(range(1, count + 1)):
            failures.append(
                f"RunActivity:{activity_name} attempt attributes are {attempts}"
            )
        for failed in runs[:-1]:
            if failed.get("status_code") != "ERROR":
                failures.append(
                    f"failed attempt of {activity_name} does not have ERROR status"
                )
        if runs[-1].get("status_code") == "ERROR":
            failures.append(f"final attempt of {activity_name} has ERROR status")

    # A worker that died mid-attempt never ended that attempt's span, so only
    # the later attempt is present, carrying its attempt number.
    for activity_name, attempt in args.expect_attempt.items():
        runs = [s for s in spans if s["name"] == f"RunActivity:{activity_name}"]
        attempts = [_attrs(s).get("temporal.activity.attempt") for s in runs]
        if attempts != [attempt]:
            failures.append(
                f"expected one RunActivity:{activity_name} span with attempt {attempt}, "
                f"found attempts {attempts}"
            )
    return failures


def _verify_agents(
    args: argparse.Namespace, trace_id: str, spans: list[dict[str, Any]]
) -> list[str]:
    """Looser checks for the OpenAI Agents scenario, whose span names come from
    the Agents SDK and the OpenInference instrumentation."""
    failures: list[str] = []
    _verify_common(trace_id, spans, failures, args)
    actual = _build_tree(spans)
    print(f"Trace {trace_id}: {len(spans)} spans")
    _print_tree(actual)
    kinds = {str(s.get("span_kind")) for s in spans}
    for kind in ("AGENT", "LLM", "TOOL", "CHAIN"):
        if kind not in kinds:
            failures.append(f"no span of kind {kind}")
    if "UNKNOWN" in kinds:
        failures.append("spans with UNKNOWN kind present")
    executes = [s for s in spans if s["name"] == "temporal:executeWorkflow"]
    if len(executes) != args.expect_runs:
        failures.append(
            f"expected {args.expect_runs} temporal:executeWorkflow spans, found {len(executes)}"
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--trace-id", help="Trace ID printed by the starter")
    parser.add_argument(
        "--workflow-id", help="Workflow ID (resolved through the RunWorkflow span)"
    )
    parser.add_argument(
        "--scenario", choices=["ticket-triage", "agents"], default="ticket-triage"
    )
    parser.add_argument(
        "--expect", choices=["approved", "declined"], default="approved"
    )
    parser.add_argument(
        "--expect-attempts",
        action="append",
        default=[],
        metavar="ACTIVITY=N",
        help="Expect N RunActivity spans (attempts) for ACTIVITY, for example classify_ticket=2",
    )
    parser.add_argument(
        "--expect-attempt",
        action="append",
        default=[],
        metavar="ACTIVITY=N",
        help="Expect the single surviving RunActivity span for ACTIVITY to carry attempt N "
        "(earlier attempts died with a killed worker and were never exported)",
    )
    parser.add_argument(
        "--expect-runs",
        type=int,
        default=1,
        help="Number of workflow runs sharing the trace (after a reset), default 1",
    )
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    if not args.trace_id and not args.workflow_id:
        parser.error("one of --trace-id or --workflow-id is required")
    args.expect_attempts = {
        item.split("=", 1)[0]: int(item.split("=", 1)[1])
        for item in args.expect_attempts
    }
    args.expect_attempt = {
        item.split("=", 1)[0]: int(item.split("=", 1)[1])
        for item in args.expect_attempt
    }

    trace_id = args.trace_id
    if not trace_id:
        trace_ids = _trace_ids_for_workflow(args.workflow_id, args.scenario)
        if not trace_ids:
            print(f"FAIL: no trace found for workflow id {args.workflow_id}")
            return 1
        if len(trace_ids) > 1:
            print(
                f"Workflow {args.workflow_id} has {len(trace_ids)} traces; verifying the newest"
            )
        trace_id = trace_ids[0]

    spans = _poll_stable_trace(trace_id, args.timeout)
    verify = _verify_agents if args.scenario == "agents" else _verify_ticket_triage
    failures = verify(args, trace_id, spans)
    print(f"Phoenix: {_trace_url(trace_id)}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: tree shape, span kinds, enrichment, and LLM spans all match")
    return 0


if __name__ == "__main__":
    sys.exit(main())

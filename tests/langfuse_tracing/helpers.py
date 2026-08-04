"""Test helpers for the langfuse_tracing sample tests."""

from typing import Iterable, List, Optional

from opentelemetry.sdk.trace import ReadableSpan


def dump_spans(
    spans: Iterable[ReadableSpan],
    *,
    parent_id: Optional[int] = None,
    indent_depth: int = 0,
) -> List[str]:
    """Render spans as an indented tree, one line per span.

    Mirrors the helper used by the Temporal Python SDK's own OpenTelemetry
    tests so span hierarchies can be asserted with a whole-tree equality.
    """
    ret: List[str] = []
    for span in spans:
        if (not span.parent and parent_id is None) or (
            span.parent and span.parent.span_id == parent_id
        ):
            ret.append(f"{'  ' * indent_depth}{span.name}")
            ret += dump_spans(
                spans,
                parent_id=span.context.span_id if span.context else None,
                indent_depth=indent_depth + 1,
            )
    return ret

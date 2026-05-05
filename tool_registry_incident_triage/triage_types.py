"""Shared types between workflow, activity, and client."""
from __future__ import annotations

import dataclasses
from typing import Literal


@dataclasses.dataclass
class AlertPayload:
    status: str
    labels: dict[str, str]
    annotations: dict[str, str]
    startsAt: str
    endsAt: str | None = None
    fingerprint: str | None = None


@dataclasses.dataclass
class ProposedRemediation:
    action: str
    justification: str


@dataclasses.dataclass
class TriageResult:
    status: Literal["resolved", "unresolved"]
    summary: str
    remediations: list[ProposedRemediation]


@dataclasses.dataclass
class ApprovalRequest:
    message: str
    diagnosis: str
    proposedAction: str


@dataclasses.dataclass
class ApprovalResponse:
    decision: Literal["approved", "rejected"]
    reason: str

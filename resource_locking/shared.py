from dataclasses import dataclass, field
from typing import Optional

LOCK_MANAGER_WORKFLOW_ID = "lock_manager"


@dataclass
class AcquireRequest:
    workflow_id: str


@dataclass
class AcquireResponse:
    release_signal_name: str
    resource: str


@dataclass
class AcquiredResource(AcquireResponse):
    autorelease: bool = field(default=True)

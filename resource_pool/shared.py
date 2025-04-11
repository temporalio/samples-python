from dataclasses import dataclass, field

RESOURCE_POOL_WORKFLOW_ID = "resource_pool"


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

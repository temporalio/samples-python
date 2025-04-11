from dataclasses import dataclass, field

RESOURCE_POOL_WORKFLOW_ID = "resource_pool"


@dataclass
class AcquireRequest:
    workflow_id: str


@dataclass
class AcquireResponse:
    release_key: str
    resource: str


@dataclass
class DetachedResource:
    resource: str
    release_key: str


@dataclass
class AcquiredResource:
    resource: str
    release_key: str
    detached: bool = field(default=False)

    def detach(self) -> DetachedResource:
        self.detached = True
        return DetachedResource(resource=self.resource, release_key=self.release_key)

from dataclasses import dataclass

LOCK_MANAGER_WORKFLOW_ID = "lock_manager"

@dataclass
class AcquireRequest:
    workflow_id: str

@dataclass
class AcquireResponse:
    release_signal_name: str
    resource: str

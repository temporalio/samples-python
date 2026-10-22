from dataclasses import dataclass, field

ACTIVITY_NAME = "process_conversation_step"


@dataclass(frozen=True)
class ConversationRequest:
    input_ref: str
    affinity_enabled: bool
    steps: int = 5


@dataclass(frozen=True)
class StepInput:
    step: int
    input_ref: str


@dataclass(frozen=True)
class StepResult:
    step: int
    worker_identity: str
    session_enabled: bool
    cache_hit: bool
    artifact_reads: int
    artifact_writes: int
    output_ref: str


@dataclass
class ConversationContext:
    messages: list[str]
    completed_steps: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class WorkerRegistration:
    identity: str
    session_enabled: bool
    pid: int
    task_queue: str

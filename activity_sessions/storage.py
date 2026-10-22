import hashlib
import json
import os
import re
import tempfile
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path

from activity_sessions.models import ConversationContext, WorkerRegistration


class FileArtifactStore:
    """A shared, file-backed stand-in for an external object store, not a cache."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.artifacts = directory / "artifacts"
        self.workers = directory / "workers"
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.workers.mkdir(parents=True, exist_ok=True)

    def write(self, context: ConversationContext) -> str:
        data = json.dumps(asdict(context), sort_keys=True).encode()
        reference = hashlib.sha256(data).hexdigest()
        self._atomic_write(self.artifacts / f"{reference}.json", data)
        return reference

    def read(self, reference: str) -> ConversationContext:
        if not re.fullmatch(r"[0-9a-f]{64}", reference):
            raise ValueError("An artifact reference must be a SHA-256 digest")
        data = (self.artifacts / f"{reference}.json").read_bytes()
        if hashlib.sha256(data).hexdigest() != reference:
            raise ValueError(f"Artifact checksum mismatch: {reference}")
        return ConversationContext(**json.loads(data))

    def register_worker(self, worker: WorkerRegistration) -> None:
        path = (
            self.workers
            / f"{hashlib.sha256(worker.identity.encode()).hexdigest()}.json"
        )
        if path.exists():
            raise ValueError(
                f"{worker.identity!r} is already registered. Use a unique identity "
                "or a fresh store directory if a previous process crashed."
            )
        self._atomic_write(path, json.dumps(asdict(worker)).encode())

    def unregister_worker(self, worker: WorkerRegistration) -> None:
        path = (
            self.workers
            / f"{hashlib.sha256(worker.identity.encode()).hexdigest()}.json"
        )
        with suppress(FileNotFoundError):
            if WorkerRegistration(**json.loads(path.read_bytes())) == worker:
                path.unlink()

    def list_workers(self, task_queue: str) -> list[WorkerRegistration]:
        workers = []
        for path in self.workers.glob("*.json"):
            with suppress(FileNotFoundError):
                worker = WorkerRegistration(**json.loads(path.read_bytes()))
                if worker.task_queue == task_queue:
                    workers.append(worker)
        return sorted(workers, key=lambda worker: worker.identity)

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        # Readers in other processes must never observe a partially written artifact.
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            try:
                output.write(data)
                output.close()
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)

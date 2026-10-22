from __future__ import annotations

TASK_QUEUE = "openai-agents-sandbox-task-queue"

# Name the worker registers its SandboxClientProvider under, and the name the
# workflow passes to temporal_sandbox_client(). The two must match exactly:
# the name becomes the prefix of that backend's activity names, which is what
# lets several backends share one worker.
SANDBOX_PROVIDER = "local"

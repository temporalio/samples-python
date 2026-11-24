"""A ``SandboxAgent`` whose sandbox operations run as Temporal activities.

``SandboxAgent`` gives an agent a real machine to work on: it can run shell
commands and read and write files. The plugin routes every one of those
operations — creating the session, each ``exec``, each read and write, and the
teardown — through a Temporal activity against the sandbox client provider
registered on the worker under the name passed to
``temporal_sandbox_client()``.

Two consequences worth knowing:

1. Each sandbox operation is individually retryable and shows up in workflow
   history, so a flaky command is a retried activity rather than a lost run.
2. The sandbox session state is serialized with the workflow. With a hosted
   backend, a worker restart mid-run resumes against the same session. A
   local sandbox lives on the worker that created it. If that worker is
   unavailable, the next operation reaches its schedule-to-start timeout.
   If a worker receives an operation for a sandbox it no longer has, it
   raises ``SandboxLost``.

This sample uses the local Unix backend, which runs commands on the worker
host and needs no credentials. Swap in a remote client such as
``DaytonaSandboxClient`` for anything you would not run on your own machine —
only the worker changes, the workflow just names a different provider.
"""

from __future__ import annotations

from datetime import timedelta

from agents import Runner
from agents.run import RunConfig
from agents.sandbox import SandboxAgent, SandboxRunConfig
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClientOptions
from temporalio import workflow
from temporalio.openai_agents.workflow import temporal_sandbox_client
from temporalio.workflow import ActivityConfig

from openai_agents.sandbox.shared import SANDBOX_PROVIDER


# @@@SNIPSTART python-openai-agents-sandbox-workflow
@workflow.defn
class LocalSandboxWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        # A default SandboxAgent already carries the Filesystem, Shell, and
        # Compaction capabilities, so there are no tools to declare here.
        agent = SandboxAgent[None](
            name="Sandbox Assistant",
            instructions=(
                "You have a sandbox with a shell and a filesystem. Use it to do "
                "the work rather than answering from memory, then report what "
                "the commands returned."
            ),
        )

        result = await Runner.run(
            starting_agent=agent,
            input=prompt,
            run_config=RunConfig(
                sandbox=SandboxRunConfig(
                    # Must match the name registered on the worker.
                    client=temporal_sandbox_client(
                        SANDBOX_PROVIDER,
                        config=ActivityConfig(
                            start_to_close_timeout=timedelta(minutes=5),
                            schedule_to_start_timeout=timedelta(seconds=30),
                        ),
                    ),
                    options=UnixLocalSandboxClientOptions(),
                ),
            ),
        )
        return result.final_output_as(str, raise_if_incorrect_type=True)


# @@@SNIPEND

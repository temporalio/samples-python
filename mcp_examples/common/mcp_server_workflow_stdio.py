import asyncio
import logging
import uuid
from datetime import timedelta
from typing import Any, Callable, Optional, Sequence

from mcp import (  # type:ignore
    ClientSession,
    GetPromptResult,
    ListPromptsResult,
    ListToolsResult,
)
from mcp.types import CallToolResult  # type:ignore
from temporalio import activity, workflow
from temporalio.worker import PollerBehaviorSimpleMaximum, Worker
from temporalio.workflow import ActivityConfig, ActivityHandle

from mcp_examples.common.mcp_server_nexus_service import (
    CallToolInput,
    ListToolsInput,
)

logger = logging.getLogger(__name__)


# Based on StatefulTemporalMCPServer from https://github.com/temporalio/sdk-python/pull/1021
class StdioMCPClientSessionWorkflow:
    """A stateful MCP client session implementation as a Temporal workflow.

    This class wraps an MCP server to maintain a persistent connection throughout
    the workflow execution. It creates a dedicated worker that stays connected to
    the MCP server and processes operations on a dedicated task queue.

    The caller will have to handle cases where the dedicated worker fails, as Temporal is
    unable to seamlessly recreate any lost state in that case.
    """

    def __init__(
        self,
        session: ClientSession,
        config: Optional[ActivityConfig] = None,
        connect_config: Optional[ActivityConfig] = None,
    ):
        """Initialize the stateful temporal MCP server.

        Args:
            server: Either an MCPServer instance or a string name for the server.
            config: Optional activity configuration for MCP operation activities.
                   Defaults to 1-minute start-to-close and 30-second schedule-to-start timeouts.
            connect_config: Optional activity configuration for the connection activity.
                           Defaults to 1-hour start-to-close timeout.
        """
        self.session = session
        self._name = str(uuid.uuid4())  # TODO
        self.config = config or ActivityConfig(
            start_to_close_timeout=timedelta(minutes=1),
            schedule_to_start_timeout=timedelta(seconds=30),
        )
        self.connect_config = connect_config or ActivityConfig(
            start_to_close_timeout=timedelta(hours=1),
        )
        self._connect_handle: Optional[ActivityHandle] = None
        super().__init__()

    @property
    def name(self) -> str:
        """Get the server name with '-stateful' suffix.

        Returns:
            The server name with '-stateful' appended.
        """
        return self._name

    async def connect(self) -> None:
        """Connect to the MCP server and start the dedicated worker.

        This method creates a dedicated task queue for this workflow and starts
        a long-running activity that maintains the connection and runs a worker
        to handle MCP operations.
        """
        self.config["task_queue"] = workflow.info().workflow_id + "-" + self.name
        self._connect_handle = workflow.start_activity(
            self.name + "-connect",
            args=[],
            **self.connect_config,
        )

    async def cleanup(self) -> None:
        """Clean up the MCP server connection.

        This method cancels the long-running connection activity, which will
        cause the dedicated worker to shut down and the MCP server connection
        to be closed.
        """
        if self._connect_handle:
            self._connect_handle.cancel()

    async def __aenter__(self):
        """Async context manager entry point.

        Returns:
            This server instance after connecting.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Async context manager exit point.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_value: Exception value if an exception occurred.
            traceback: Exception traceback if an exception occurred.
        """
        await self.cleanup()

    async def list_tools(
        self,
        input: ListToolsInput,
    ) -> ListToolsResult:
        """List available tools from the MCP server.

        This method executes a Temporal activity on the dedicated task queue
        to retrieve the list of available tools from the persistent MCP connection.

        Args:
            run_context: Optional run context wrapper (unused in stateful mode).
            agent: Optional agent base (unused in stateful mode).

        Returns:
            A list of available MCP tools.

        Raises:
            ApplicationError: If the MCP worker fails to schedule or heartbeat.
            ActivityError: If the underlying Temporal activity fails.
        """
        logger.info("Executing list-tools: %s", self.config)
        return await workflow.execute_activity(
            self.name + "-list-tools",
            args=[input],
            result_type=ListToolsResult,
            **self.config,
        )

    async def call_tool(self, input: CallToolInput) -> CallToolResult:
        """Call a specific tool on the MCP server.

        This method executes a Temporal activity on the dedicated task queue
        to call the specified tool using the persistent MCP connection.

        Args:
            tool_name: The name of the tool to call.
            arguments: Optional dictionary of arguments to pass to the tool.

        Returns:
            The result of the tool call.

        Raises:
            ActivityError: If the underlying Temporal activity fails.
        """
        return await workflow.execute_activity(
            self.name + "-call-tool",
            args=[input],
            result_type=CallToolResult,
            **self.config,
        )

    async def list_prompts(self) -> ListPromptsResult:
        """List available prompts from the MCP server.

        This method executes a Temporal activity on the dedicated task queue
        to retrieve the list of available prompts from the persistent MCP connection.

        Returns:
            A list of available prompts.

        Raises:
            ActivityError: If the underlying Temporal activity fails.
        """
        return await workflow.execute_activity(
            self.name + "-list-prompts",
            args=[],
            result_type=ListPromptsResult,
            **self.config,
        )

    async def get_prompt(
        self, name: str, arguments: Optional[dict[str, Any]] = None
    ) -> GetPromptResult:
        """Get a specific prompt from the MCP server.

        This method executes a Temporal activity on the dedicated task queue
        to retrieve the specified prompt using the persistent MCP connection.

        Args:
            name: The name of the prompt to retrieve.
            arguments: Optional dictionary of arguments for the prompt.

        Returns:
            The prompt result.

        Raises:
            ActivityError: If the underlying Temporal activity fails.
        """
        return await workflow.execute_activity(
            self.name + "-get-prompt",
            args=[name, arguments],
            result_type=GetPromptResult,
            **self.config,
        )

    def get_activities(self) -> Sequence[Callable]:
        """Get the Temporal activities for this stateful MCP server.

        Creates and returns the Temporal activity functions that handle MCP operations
        and connection management. This includes a long-running connect activity that
        maintains the MCP connection and runs a dedicated worker.

        Returns:
            A sequence containing the connect activity function.

        Raises:
            ValueError: If no MCP server instance was provided during initialization.
        """
        session = self.session
        if session is None:
            raise ValueError(
                "A full MCPServer implementation should have been provided when adding a server to the worker."
            )

        @activity.defn(name=self.name + "-list-tools")
        async def list_tools() -> ListToolsResult:
            return await session.list_tools()

        @activity.defn(name=self.name + "-call-tool")
        async def call_tool(
            tool_name: str, arguments: Optional[dict[str, Any]]
        ) -> CallToolResult:
            return await session.call_tool(tool_name, arguments)

        @activity.defn(name=self.name + "-list-prompts")
        async def list_prompts() -> ListPromptsResult:
            return await session.list_prompts()

        @activity.defn(name=self.name + "-get-prompt")
        async def get_prompt(
            name: str, arguments: Optional[dict[str, Any]]
        ) -> GetPromptResult:
            return await session.get_prompt(name, arguments)

        async def heartbeat_every(delay: float, *details: Any) -> None:
            """Heartbeat every so often while not cancelled"""
            while True:
                await asyncio.sleep(delay)
                activity.heartbeat(*details)

        @activity.defn(name=self.name + "-connect")
        async def connect() -> None:
            logger.info("Connect activity")
            heartbeat_task = asyncio.create_task(heartbeat_every(30))
            try:
                # await session.connect()

                worker = Worker(
                    activity.client(),
                    task_queue=activity.info().workflow_id + "-" + self.name,
                    activities=[list_tools, call_tool, list_prompts, get_prompt],
                    activity_task_poller_behavior=PollerBehaviorSimpleMaximum(1),
                )

                await worker.run()
            finally:
                # await session.cleanup()
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

        return (connect,)

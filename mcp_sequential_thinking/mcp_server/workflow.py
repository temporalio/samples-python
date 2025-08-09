from temporalio import workflow


@workflow.defn
class SequentialThinkingMCPServer:
    def __init__(self) -> None:
        self.running = False

    @workflow.run
    async def start(self):
        self.running = True
        await workflow.wait_condition(lambda: not self.running)

    @workflow.update
    def stop(self):
        self.running = False

    @workflow.update
    async def call_tool(self):
        pass

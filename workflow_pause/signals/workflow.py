from temporalio import workflow


@workflow.defn
class SignalPauseWorkflow:
    """Collects messages delivered by signal until a "done" signal arrives.

    Signals sent while the workflow is paused are accepted and recorded in
    history, but the signal handler does not run until the workflow is
    unpaused — at which point the buffered signals are processed in order.
    """

    def __init__(self) -> None:
        self._messages: list[str] = []
        self._done = False

    @workflow.run
    async def run(self) -> list[str]:
        await workflow.wait_condition(lambda: self._done)
        return self._messages

    @workflow.signal
    async def add_message(self, message: str) -> None:
        if message == "done":
            self._done = True
            return
        workflow.logger.info("Received message: %s", message)
        self._messages.append(message)

    @workflow.query
    def messages(self) -> list[str]:
        return self._messages

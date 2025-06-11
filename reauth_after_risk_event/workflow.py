from datetime import timedelta
from temporalio import workflow

# Signal to be sent when user completes reauthentication
@workflow.defn
class ReauthenticationAfterRiskEventWorkflow:
    def __init__(self):
        self.reauthenticated = False

    @workflow.signal
    async def complete_reauthentication(self):
        self.reauthenticated = True

    @workflow.run
    async def run(self, user_id: str, timeout_minutes: int = 10) -> str:
        workflow.logger.info(f"Started reauth workflow for user: {user_id}")

        # Wait for signal or timeout
        try:
            await workflow.wait_condition(
                lambda: self.reauthenticated,
                timeout=timedelta(minutes=timeout_minutes)
            )
        except TimeoutError:
            workflow.logger.warn("Timeout waiting for reauthentication")
            return "failed_timeout"

        workflow.logger.info("User successfully reauthenticated")
        return "success"

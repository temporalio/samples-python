import asyncio
import subprocess
import os
import pytest


class IntegrationTestRunner:
    """Helper class to manage worker and workflow execution"""

    def __init__(self):
        self.worker_process = None

    async def start_worker(self):
        """Start the worker process"""
        print("Starting worker process...")
        self.worker_process = subprocess.Popen(
            ["uv", "run", "python", "worker.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Give worker time to start up
        await asyncio.sleep(3)

        # Check if worker started successfully
        if self.worker_process.poll() is not None:
            stdout, stderr = self.worker_process.communicate()
            raise RuntimeError(
                f"Worker failed to start. stdout: {stdout}, stderr: {stderr}"
            )

    def stop_worker(self):
        """Stop the worker process"""
        if self.worker_process:
            print("Stopping worker process...")
            self.worker_process.terminate()
            try:
                self.worker_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.worker_process.kill()
                self.worker_process.wait()

    async def run_workflow(self, query: str | None = None):
        """Run the workflow and return the exit code"""
        if query is None:
            query = "What is the capital of France?"

        print(f"Running workflow with query: {query}")

        process = subprocess.Popen(
            ["uv", "run", "python", "start_workflow.py", query],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, stderr = process.communicate(timeout=60)  # Increased timeout
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                stdout, stderr = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", ""
            return -1, stdout or "", stderr or "Process timed out"

        print(f"Workflow stdout: {stdout}")
        if stderr:
            print(f"Workflow stderr: {stderr}")

        return process.returncode, stdout, stderr


@pytest.mark.asyncio
@pytest.mark.timeout(180)  # 3 minute timeout for integration test
async def test_worker_and_workflow_integration():
    """Integration test that starts worker and runs workflow to completion"""
    # Require OpenAI API key - fail if not available
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is required for integration test"
        )

    runner = IntegrationTestRunner()

    try:
        # Start the worker
        await runner.start_worker()

        # Give worker extra time to fully initialize
        await asyncio.sleep(2)

        # Run the workflow with a simple query
        exit_code, stdout, stderr = await runner.run_workflow("What is 2+2?")

        # Validate successful execution
        assert exit_code == 0, (
            f"Workflow failed with exit code {exit_code}. stderr: {stderr}"
        )
        assert "RESEARCH COMPLETED!" in stdout, "Workflow did not complete successfully"

        print("✅ Integration test passed: Worker and workflow completed successfully")

    finally:
        # Always stop the worker
        runner.stop_worker()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

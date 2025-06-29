#!/usr/bin/env python3
"""
End-to-End Test Runner for OpenAI Agents Expense Processing

This script runs comprehensive E2E tests for all starter.py scenarios.
It ensures the environment is properly set up and runs all test cases.

Usage:
    python run_e2e_tests.py                    # Run all E2E tests
    python run_e2e_tests.py --verbose          # Run with verbose output
    python run_e2e_tests.py --single expense_1 # Run single test
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def check_environment():
    """Check that the environment is properly configured"""
    print("🔍 Checking environment setup...")

    # Check .env file
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        print("❌ .env file not found in samples-python-2/")
        print("   Please create a .env file with OPENAI_API_KEY=your_key")
        return False

    # Load .env file
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except ImportError:
        # Manual loading if python-dotenv not available
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in .env file")
        print("   Please add OPENAI_API_KEY=your_key to the .env file")
        return False

    print("✅ Environment setup is valid")
    return True


def check_temporal_server():
    """Check if Temporal server is running"""
    print("🔍 Checking Temporal server...")

    try:
        # Use the Temporal client to properly check connectivity
        import asyncio

        from temporalio.client import Client

        async def test_connection():
            try:
                # Simply try to connect - this will fail if server is not running
                await Client.connect("localhost:7233")
                return True
            except Exception as e:
                print(f"❌ Cannot connect to Temporal server: {e}")
                return False

        # Run the async connection test
        is_connected = asyncio.run(test_connection())

        if is_connected:
            print("✅ Temporal server is running")
            return True
        else:
            print("   Please start the Temporal server with: temporal server start-dev")
            return False

    except Exception as e:
        print(f"❌ Cannot connect to Temporal server: {e}")
        print("   Please start the Temporal server with: temporal server start-dev")
        return False


def run_tests(test_args):
    """Run the E2E tests with pytest"""
    print("🚀 Running E2E tests...")

    # Base pytest command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(Path(__file__).parent / "test_starter_e2e.py"),
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
    ]

    # Add additional arguments
    cmd.extend(test_args)

    try:
        subprocess.run(cmd, check=True, cwd=Path(__file__).parent.parent.parent)
        print("✅ All E2E tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run E2E tests for OpenAI Agents Expense Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run all E2E tests
  %(prog)s --verbose          # Run with extra verbose output
  %(prog)s --single expense_1 # Run single test case
  %(prog)s --env-only         # Just check environment setup
        """,
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable extra verbose output"
    )

    parser.add_argument(
        "--single",
        "-s",
        choices=["expense_1", "expense_2", "expense_3", "batch", "ui", "env"],
        help="Run single test case",
    )

    parser.add_argument(
        "--env-only", action="store_true", help="Only check environment setup"
    )

    parser.add_argument(
        "--no-server-check",
        action="store_true",
        help="Skip Temporal server connectivity check",
    )

    args = parser.parse_args()

    print("OpenAI Agents Expense Processing - E2E Test Runner")
    print("=" * 60)

    # Check environment
    if not check_environment():
        sys.exit(1)

    if args.env_only:
        print("🎉 Environment check completed successfully!")
        return

    # Check Temporal server (unless skipped)
    if not args.no_server_check:
        if not check_temporal_server():
            print("\n💡 Tip: Start Temporal server with: temporal server start-dev")
            sys.exit(1)

    # Prepare test arguments
    test_args = []

    if args.verbose:
        test_args.extend(["-vv", "-s"])

    if args.single:
        # Map single test names to pytest patterns
        test_patterns = {
            "expense_1": "test_expense_1_auto_approval",
            "expense_2": "test_expense_2_human_approval",
            "expense_3": "test_expense_3_human_rejection",
            "batch": "test_all_expenses_batch_processing",
            "ui": "test_ui_integration_mock_server",
            "env": "test_environment_setup",
        }
        test_args.extend(["-k", test_patterns[args.single]])

    # Run the tests
    success = run_tests(test_args)

    if success:
        print("\n🎉 All E2E tests completed successfully!")
        print("💡 The OpenAI Agents Expense Processing system is working correctly")
    else:
        print("\n❌ Some tests failed. Please check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()

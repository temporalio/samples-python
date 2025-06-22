#!/usr/bin/env python3
"""
Test runner for OpenAI Agents Expense Processing Sample

This script provides an easy way to run tests with proper setup and configuration.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def setup_environment():
    """Set up the test environment"""
    # Add the current directory to Python path
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # Set environment variables for testing
    os.environ.setdefault("PYTHONPATH", str(current_dir))
    os.environ.setdefault("TEMPORAL_NAMESPACE", "default")
    
    print(f"Python path: {sys.path[0]}")
    print(f"Current directory: {current_dir}")


def run_tests(test_type="all", verbose=False, coverage=False):
    """Run the specified tests"""
    setup_environment()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test path
    test_dir = Path(__file__).parent / "tests"
    cmd.append(str(test_dir))
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=openai_agents_expense", "--cov-report=html", "--cov-report=term"])
    
    # Filter tests by type
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "openai":
        cmd.extend(["-m", "openai"])
    elif test_type != "all":
        print(f"Unknown test type: {test_type}")
        return 1
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 130
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run tests for OpenAI Agents Expense Processing")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "openai"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests with verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run tests with coverage reporting"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run a quick subset of tests (unit tests only)"
    )
    
    args = parser.parse_args()
    
    # Quick mode overrides type
    if args.quick:
        test_type = "unit"
    else:
        test_type = args.type
    
    print("OpenAI Agents Expense Processing - Test Runner")
    print("=" * 50)
    print(f"Test type: {test_type}")
    print(f"Verbose: {args.verbose}")
    print(f"Coverage: {args.coverage}")
    print()
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("WARNING: Tests require Python 3.9+")
        print(f"Current version: {sys.version}")
        return 1
    
    if sys.version_info < (3, 11):
        print("WARNING: OpenAI tests will be skipped on Python < 3.11")
        print(f"Current version: {sys.version}")
    
    return run_tests(test_type, args.verbose, args.coverage)


if __name__ == "__main__":
    sys.exit(main()) 
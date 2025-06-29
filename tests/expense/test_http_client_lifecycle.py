#!/usr/bin/env python3
"""
Simple test script to verify HTTP client lifecycle management.
"""

import asyncio
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from expense.activities import (
    cleanup_http_client,
    create_expense_activity,
    get_http_client,
    initialize_http_client,
)


async def test_http_client_lifecycle():
    """Test that HTTP client lifecycle management works correctly."""
    print("Testing HTTP client lifecycle management...")

    # Test 1: Client should not be initialized initially
    try:
        get_http_client()
        print("❌ FAIL: Expected RuntimeError when client not initialized")
        return False
    except RuntimeError as e:
        print(f"✅ PASS: Got expected error when client not initialized: {e}")

    # Test 2: Initialize client
    await initialize_http_client()
    print("✅ PASS: HTTP client initialized")

    # Test 3: Client should be available now
    try:
        client = get_http_client()
        print(f"✅ PASS: Got HTTP client: {type(client).__name__}")
    except Exception as e:
        print(f"❌ FAIL: Could not get HTTP client after initialization: {e}")
        return False

    # Test 4: Test multiple initializations (should be safe)
    await initialize_http_client()
    client2 = get_http_client()
    if client is client2:
        print("✅ PASS: Multiple initializations return same client instance")
    else:
        print("❌ FAIL: Multiple initializations created different clients")
        return False

    # Test 5: Cleanup client
    await cleanup_http_client()
    print("✅ PASS: HTTP client cleaned up")

    # Test 6: Client should not be available after cleanup
    try:
        get_http_client()
        print("❌ FAIL: Expected RuntimeError after cleanup")
        return False
    except RuntimeError as e:
        print(f"✅ PASS: Got expected error after cleanup: {e}")

    print("\n🎉 All HTTP client lifecycle tests passed!")
    return True


async def test_activity_integration():
    """Test that activities can use the HTTP client (mock test)."""
    print("\nTesting activity integration...")

    # Initialize client for activities
    await initialize_http_client()

    try:
        # This will fail because the expense server isn't running,
        # but it will test that the HTTP client is accessible
        await create_expense_activity("test-expense-123")
        print("❌ Unexpected: Activity succeeded (expense server must be running)")
    except Exception as e:
        # We expect this to fail since expense server isn't running
        if "HTTP client not initialized" in str(e):
            print("❌ FAIL: HTTP client not accessible in activity")
            return False
        else:
            print(
                f"✅ PASS: Activity accessed HTTP client correctly (failed as expected due to no server): {type(e).__name__}"
            )

    # Cleanup
    await cleanup_http_client()
    print("✅ PASS: Activity integration test completed")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("HTTP Client Lifecycle Management Tests")
    print("=" * 60)

    test1_passed = await test_http_client_lifecycle()
    test2_passed = await test_activity_integration()

    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print(
            "🎉 ALL TESTS PASSED! HTTP client lifecycle management is working correctly."
        )
        return 0
    else:
        print("❌ SOME TESTS FAILED! Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

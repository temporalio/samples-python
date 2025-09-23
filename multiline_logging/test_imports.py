#!/usr/bin/env python3
"""
Test that all imports work correctly
"""

try:
    from .interceptor import MultilineLoggingInterceptor

    print("✅ Interceptor imports successfully")

    from .activities import complex_failing_activity, failing_activity

    print("✅ Activities import successfully")

    from .workflows import MultilineLoggingWorkflow

    print("✅ Workflows import successfully")

    print("✅ All imports work correctly!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

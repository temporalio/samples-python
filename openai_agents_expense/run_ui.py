#!/usr/bin/env python3
"""
Run the OpenAI Agents Expense UI Server.

This script starts the web-based expense management UI that integrates with
the AI agents expense processing workflows.

Usage:
  python run_ui.py

The UI will be available at http://localhost:8099
"""

import asyncio

from .ui import main

if __name__ == "__main__":
    print("Starting OpenAI Agents Expense UI...")
    print("The UI will be available at http://localhost:8099")
    print("Press Ctrl+C to stop the server")
    asyncio.run(main())

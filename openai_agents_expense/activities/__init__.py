"""
Activities for the OpenAI Agents Expense Processing Sample.

This package contains Temporal activities used by the AI agents:
- Web search activity for vendor validation and business context
"""

from .web_search import web_search_activity

__all__ = [
    "web_search_activity"
] 
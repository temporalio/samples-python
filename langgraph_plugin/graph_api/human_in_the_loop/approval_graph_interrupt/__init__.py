"""Approval Workflow Sample.

Demonstrates human-in-the-loop approval pattern using LangGraph's interrupt()
with Temporal signals for receiving human input.

Components:
- graph.py: LangGraph graph with approval node using interrupt()
- workflow.py: Temporal workflow that handles interrupts and signals
- run_worker.py: Worker setup with LangGraphPlugin
- run_workflow.py: Client that starts workflow and sends approval signal
"""

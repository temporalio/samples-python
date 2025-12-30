"""Approval Workflow Sample (Signal-based).

Demonstrates human-in-the-loop approval pattern using run_in_workflow=True
to access Temporal signals directly from graph nodes.

Components:
- graph.py: LangGraph graph with approval node using run_in_workflow=True
- workflow.py: Temporal workflow definition
- run_worker.py: Worker setup with LangGraphPlugin
- run_workflow.py: Client that starts workflow
- run_respond.py: Script to send approval signals
"""

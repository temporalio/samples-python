"""
This file re-exports the Nexus service from the hello_nexus sample.

The nexus_cancel sample demonstrates cancellation using the same service
definition as hello_nexus to show how to cancel operations.
"""

# Re-export the service from hello_nexus
from hello_nexus.service import MyInput, MyNexusService, MyOutput

__all__ = ["MyInput", "MyNexusService", "MyOutput"]

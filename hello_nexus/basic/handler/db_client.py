from __future__ import annotations


class MyDBClient:
    """
    This class represents a resource that your Nexus operation handlers may need when they
    are handling Nexus requests, but which is only available when the Nexus worker is
    started. Notice that:

    (a) The user's service handler class __init__ constructor takes a MyDBClient instance
        (see hello_nexus.handler.MyNexusService)

    (b) The user is responsible for instantiating the service handler class when they
        start the worker (see hello_nexus.handler.worker), so they can pass any
        necessary resources (such as this database client) to the service handler.
    """

    @classmethod
    def connect(cls) -> MyDBClient:
        return cls()

    def execute(self, query: str) -> str:
        return "query-result"

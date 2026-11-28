from dataclasses import dataclass

import nexusrpc

COMPRESSED_ENCRYPTED_1_ENDPOINT = "nexus-serialization-compressed-encrypted-1"
COMPRESSED_ENCRYPTED_2_ENDPOINT = "nexus-serialization-compressed-encrypted-2"
ENCRYPTED_1_ENDPOINT = "nexus-serialization-encrypted-1"
ENCRYPTED_2_ENDPOINT = "nexus-serialization-encrypted-2"

ENDPOINTS = (
    COMPRESSED_ENCRYPTED_1_ENDPOINT,
    COMPRESSED_ENCRYPTED_2_ENDPOINT,
    ENCRYPTED_1_ENDPOINT,
    ENCRYPTED_2_ENDPOINT,
)

CALLER_NAMESPACE = "nexus-serialization-caller"
COMPRESSED_ENCRYPTED_NAMESPACE = "nexus-serialization-compressed-encrypted-handler"
ENCRYPTED_NAMESPACE = "nexus-serialization-encrypted-handler"


@nexusrpc.service
class SyncEchoService:
    echo: nexusrpc.Operation[str, str]


@nexusrpc.service
class AsyncEchoService:
    echo_async: nexusrpc.Operation[str, str] = nexusrpc.Operation(name="echoAsync")


@dataclass
class EndpointResults:
    sync: str
    async_result: str

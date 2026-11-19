import zlib

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from temporalio.api.common.v1 import Payload
from temporalio.converter import (
    DataConverter,
    NexusSerializationContext,
    WorkflowSerializationContext,
)

from codec import EncryptionCodec
from config import (
    caller_data_converter,
    compressed_encrypted_data_converter,
    encrypted_data_converter,
)
from service import (
    COMPRESSED_ENCRYPTED_1_ENDPOINT,
    COMPRESSED_ENCRYPTED_2_ENDPOINT,
    ENCRYPTED_1_ENDPOINT,
    ENCRYPTED_2_ENDPOINT,
)


@pytest.mark.parametrize(
    "endpoint,handler_factory,key_id",
    [
        (
            COMPRESSED_ENCRYPTED_1_ENDPOINT,
            compressed_encrypted_data_converter,
            "compressed-encrypted-1",
        ),
        (
            COMPRESSED_ENCRYPTED_2_ENDPOINT,
            compressed_encrypted_data_converter,
            "compressed-encrypted-2",
        ),
        (ENCRYPTED_1_ENDPOINT, encrypted_data_converter, "encrypted-1"),
        (ENCRYPTED_2_ENDPOINT, encrypted_data_converter, "encrypted-2"),
    ],
)
async def test_caller_and_handlers_use_the_key_for_each_endpoint(
    endpoint, handler_factory, key_id
):
    context = NexusSerializationContext(endpoint, "SyncEchoService", "echo")
    caller = caller_data_converter().with_context(context)
    handler = handler_factory().with_context(context)

    [request] = await caller.encode(["hello"])
    assert request.metadata == {
        "encoding": b"binary/nexus-aes-gcm",
        "encryption-key-id": key_id.encode(),
        "nexus-endpoint-name": endpoint.encode(),
    }
    [plain] = await DataConverter.default.encode(["plain"])
    assert await handler.decode([plain, request], [str, str]) == ["plain", "hello"]

    [result] = await handler.encode(["reply"])
    assert result.metadata == request.metadata
    assert await caller.decode([result], [str]) == ["reply"]


@pytest.mark.parametrize(
    "compressed_endpoint,encrypted_endpoint",
    [
        (COMPRESSED_ENCRYPTED_1_ENDPOINT, ENCRYPTED_1_ENDPOINT),
        (COMPRESSED_ENCRYPTED_2_ENDPOINT, ENCRYPTED_2_ENDPOINT),
    ],
)
async def test_compresses_before_encrypting_with_either_key(
    compressed_endpoint, encrypted_endpoint
):
    message = "repeat me " * 100
    converter = caller_data_converter()
    compressed_converter = converter.with_context(
        NexusSerializationContext(compressed_endpoint, "SyncEchoService", "echo")
    )
    encrypted_converter = converter.with_context(
        NexusSerializationContext(encrypted_endpoint, "SyncEchoService", "echo")
    )
    [compressed] = await compressed_converter.encode([message])
    [encrypted] = await encrypted_converter.encode([message])
    assert len(compressed.data) < len(encrypted.data)
    assert await compressed_converter.decode([compressed], [str]) == [message]


async def test_caller_workflow_payloads_use_their_own_key():
    converter = caller_data_converter().with_context(
        WorkflowSerializationContext("nexus-serialization-caller", "caller-id")
    )
    results = {
        ENCRYPTED_1_ENDPOINT: {"sync": "Hello from Nexus", "async_result": "reply"}
    }
    for value in ("Hello from Nexus", results):
        [payload] = await converter.encode([value])
        assert payload.metadata == {
            "encoding": b"binary/nexus-aes-gcm",
            "encryption-key-id": b"caller-workflow",
        }
        assert b"Hello from Nexus" not in payload.data
        assert await converter.decode([payload]) == [value]


async def test_rejects_unknown_endpoints():
    with pytest.raises(ValueError, match="Unknown Nexus endpoint: unknown"):
        converter = caller_data_converter().with_context(
            NexusSerializationContext("unknown", "SyncEchoService", "echo")
        )
        await converter.encode(["hello"])


@pytest.mark.parametrize(
    "factory,endpoint,expected_key,compressed",
    [
        (
            caller_data_converter,
            COMPRESSED_ENCRYPTED_1_ENDPOINT,
            b"handler-a-key-01",
            True,
        ),
        (
            caller_data_converter,
            COMPRESSED_ENCRYPTED_2_ENDPOINT,
            b"handler-a-key-02",
            True,
        ),
        (caller_data_converter, ENCRYPTED_1_ENDPOINT, b"handler-b-key-01", False),
        (caller_data_converter, ENCRYPTED_2_ENDPOINT, b"handler-b-key-02", False),
        (caller_data_converter, None, b"sample-key-C-123", False),
        (compressed_encrypted_data_converter, None, b"handler-a-key-01", False),
        (encrypted_data_converter, None, b"handler-b-key-01", False),
    ],
)
async def test_selects_the_expected_raw_key_and_payload_format(
    factory, endpoint, expected_key, compressed
):
    context = (
        NexusSerializationContext(endpoint, "AsyncEchoService", "echoAsync")
        if endpoint
        else WorkflowSerializationContext("handler", "workflow-id")
    )
    converter = factory().with_context(context)
    [payload] = await converter.encode(["Hello from Nexus"])
    plaintext = AESGCM(expected_key).decrypt(payload.data[:12], payload.data[12:], None)
    inner = Payload.FromString(plaintext)
    if compressed:
        assert inner.metadata == {"encoding": b"binary/nexus-zlib"}
        inner = Payload.FromString(zlib.decompress(inner.data))
    assert inner.metadata == {"encoding": b"json/plain"}
    assert await DataConverter.default.decode([inner], [str]) == ["Hello from Nexus"]


async def test_bound_converters_keep_their_context():
    base = caller_data_converter()
    first = base.with_context(
        NexusSerializationContext(ENCRYPTED_1_ENDPOINT, "SyncEchoService", "echo")
    )
    second = base.with_context(
        NexusSerializationContext(ENCRYPTED_2_ENDPOINT, "SyncEchoService", "echo")
    )
    workflow = first.with_context(WorkflowSerializationContext("caller", "workflow-id"))

    for converter, endpoint, key_id, key in [
        (first, ENCRYPTED_1_ENDPOINT, "encrypted-1", b"handler-b-key-01"),
        (second, ENCRYPTED_2_ENDPOINT, "encrypted-2", b"handler-b-key-02"),
        (base, None, "caller-workflow", b"sample-key-C-123"),
        (workflow, None, "caller-workflow", b"sample-key-C-123"),
    ]:
        [payload] = await converter.encode(["hello"])
        assert payload.metadata["encryption-key-id"] == key_id.encode()
        assert payload.metadata.get("nexus-endpoint-name") == (
            endpoint.encode() if endpoint else None
        )
        inner = Payload.FromString(
            AESGCM(key).decrypt(payload.data[:12], payload.data[12:], None)
        )
        assert await DataConverter.default.decode([inner], [str]) == ["hello"]
        assert await converter.decode([payload], [str]) == ["hello"]


async def test_encryption_codec_keeps_each_endpoints_metadata_separate():
    base = EncryptionCodec("shared", b"handler-b-key-01")
    first = base.with_context(
        NexusSerializationContext(ENCRYPTED_1_ENDPOINT, "SyncEchoService", "echo")
    )
    second = base.with_context(
        NexusSerializationContext(ENCRYPTED_2_ENDPOINT, "SyncEchoService", "echo")
    )
    [payload] = await DataConverter.default.encode(["hello"])
    for codec, endpoint in [
        (first, ENCRYPTED_1_ENDPOINT),
        (second, ENCRYPTED_2_ENDPOINT),
        (base, None),
    ]:
        [encrypted] = await codec.encode([payload])
        assert encrypted.metadata.get("nexus-endpoint-name") == (
            endpoint.encode() if endpoint else None
        )
        assert await codec.decode([encrypted]) == [payload]


async def test_encrypting_the_same_value_uses_a_fresh_nonce():
    converter = caller_data_converter().with_context(
        NexusSerializationContext(ENCRYPTED_1_ENDPOINT, "SyncEchoService", "echo")
    )
    [first] = await converter.encode(["hello"])
    [second] = await converter.encode(["hello"])
    assert first.data[:12] != second.data[:12]
    assert first.data != second.data
    assert await converter.decode([first], [str]) == ["hello"]
    assert await converter.decode([second], [str]) == ["hello"]


@pytest.mark.parametrize("damage", ["altered", "incomplete-nonce", "truncated-tag"])
async def test_rejects_damaged_ciphertext(damage):
    converter = caller_data_converter().with_context(
        NexusSerializationContext(ENCRYPTED_1_ENDPOINT, "SyncEchoService", "echo")
    )
    [payload] = await converter.encode(["hello"])
    if damage == "altered":
        data = bytearray(payload.data)
        data[12] ^= 1
        payload.data = bytes(data)
    elif damage == "incomplete-nonce":
        payload.data = payload.data[:1]
    else:
        payload.data = payload.data[:-1]
    with pytest.raises((InvalidTag, ValueError)):
        await converter.decode([payload], [str])

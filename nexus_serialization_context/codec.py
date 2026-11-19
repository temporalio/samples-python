import copy
import os
import zlib
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Self

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from temporalio.api.common.v1 import Payload
from temporalio.converter import (
    NexusSerializationContext,
    PayloadCodec,
    SerializationContext,
    WithSerializationContext,
)


class NexusCodec(PayloadCodec, WithSerializationContext):
    """Select an endpoint's codec, with a default for ordinary workflow payloads."""

    def __init__(
        self, endpoint_codecs: Mapping[str, PayloadCodec], workflow_codec: PayloadCodec
    ) -> None:
        self._endpoint_codecs = MappingProxyType(dict(endpoint_codecs))
        self._workflow_codec = workflow_codec
        self._selected_codec = workflow_codec

    def with_context(self, context: SerializationContext) -> Self:
        selected = self._workflow_codec
        if isinstance(context, NexusSerializationContext):
            try:
                selected = self._endpoint_codecs[context.endpoint]
            except KeyError:
                raise ValueError(
                    f"Unknown Nexus endpoint: {context.endpoint}"
                ) from None
        if isinstance(selected, WithSerializationContext):
            selected = selected.with_context(context)
        # Keep each operation's selection separate and share the read-only configuration.
        bound = copy.copy(self)
        bound._selected_codec = selected
        return bound

    async def encode(self, payloads: Sequence[Payload]) -> list[Payload]:
        return await self._selected_codec.encode(payloads)

    async def decode(self, payloads: Sequence[Payload]) -> list[Payload]:
        return await self._selected_codec.decode(payloads)


class EncryptionCodec(PayloadCodec, WithSerializationContext):
    """Encrypt the whole payload so its encoding metadata is restored on decode."""

    def __init__(self, key_id: str, key: bytes, *, compress: bool = False) -> None:
        self._key_id = key_id
        self._encryptor = AESGCM(key)
        self._compress = compress
        self._endpoint: str | None = None

    def with_context(self, context: SerializationContext) -> Self:
        bound = copy.copy(self)
        bound._endpoint = (
            context.endpoint if isinstance(context, NexusSerializationContext) else None
        )
        return bound

    async def encode(self, payloads: Sequence[Payload]) -> list[Payload]:
        encoded = []
        for payload in payloads:
            if self._compress:
                payload = Payload(
                    metadata={"encoding": b"binary/nexus-zlib"},
                    data=zlib.compress(payload.SerializeToString()),
                )
            # Store a fresh public 12-byte nonce before the ciphertext and 16-byte tag.
            nonce = os.urandom(12)
            metadata = {
                "encoding": b"binary/nexus-aes-gcm",
                "encryption-key-id": self._key_id.encode(),
            }
            if self._endpoint:
                metadata["nexus-endpoint-name"] = self._endpoint.encode()
            encoded.append(
                Payload(
                    metadata=metadata,
                    data=nonce
                    + self._encryptor.encrypt(nonce, payload.SerializeToString(), None),
                )
            )
        return encoded

    async def decode(self, payloads: Sequence[Payload]) -> list[Payload]:
        decoded = []
        for payload in payloads:
            if payload.metadata.get("encoding") != b"binary/nexus-aes-gcm":
                decoded.append(payload)
                continue
            if payload.metadata.get("encryption-key-id") != self._key_id.encode():
                raise ValueError("Unexpected encryption key ID")
            if len(payload.data) < 28:
                raise ValueError("AES-GCM payload is too short")
            plaintext = Payload.FromString(
                self._encryptor.decrypt(payload.data[:12], payload.data[12:], None)
            )
            if self._compress:
                if plaintext.metadata.get("encoding") != b"binary/nexus-zlib":
                    raise ValueError("Expected a Nexus zlib payload")
                plaintext = Payload.FromString(zlib.decompress(plaintext.data))
            decoded.append(plaintext)
        return decoded

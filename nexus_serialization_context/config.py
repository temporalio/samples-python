from temporalio.converter import DataConverter

from codec import EncryptionCodec, NexusCodec
from service import (
    COMPRESSED_ENCRYPTED_1_ENDPOINT,
    COMPRESSED_ENCRYPTED_2_ENDPOINT,
    ENCRYPTED_1_ENDPOINT,
    ENCRYPTED_2_ENDPOINT,
)

# These keys are for this local example. Load production keys from secure storage.
COMPRESSED_ENCRYPTED_KEY_1 = b"handler-a-key-01"
COMPRESSED_ENCRYPTED_KEY_2 = b"handler-a-key-02"
ENCRYPTED_KEY_1 = b"handler-b-key-01"
ENCRYPTED_KEY_2 = b"handler-b-key-02"
CALLER_WORKFLOW_KEY = b"sample-key-C-123"


def _compressed_encrypted_codecs() -> dict[str, EncryptionCodec]:
    return {
        COMPRESSED_ENCRYPTED_1_ENDPOINT: EncryptionCodec(
            "compressed-encrypted-1", COMPRESSED_ENCRYPTED_KEY_1, compress=True
        ),
        COMPRESSED_ENCRYPTED_2_ENDPOINT: EncryptionCodec(
            "compressed-encrypted-2", COMPRESSED_ENCRYPTED_KEY_2, compress=True
        ),
    }


def _encrypted_codecs() -> dict[str, EncryptionCodec]:
    return {
        ENCRYPTED_1_ENDPOINT: EncryptionCodec("encrypted-1", ENCRYPTED_KEY_1),
        ENCRYPTED_2_ENDPOINT: EncryptionCodec("encrypted-2", ENCRYPTED_KEY_2),
    }


def caller_data_converter() -> DataConverter:
    return DataConverter(
        payload_codec=NexusCodec(
            {**_compressed_encrypted_codecs(), **_encrypted_codecs()},
            EncryptionCodec("caller-workflow", CALLER_WORKFLOW_KEY),
        )
    )


def compressed_encrypted_data_converter() -> DataConverter:
    return DataConverter(
        payload_codec=NexusCodec(
            _compressed_encrypted_codecs(),
            EncryptionCodec("compressed-encrypted-1", COMPRESSED_ENCRYPTED_KEY_1),
        )
    )


def encrypted_data_converter() -> DataConverter:
    return DataConverter(
        payload_codec=NexusCodec(
            _encrypted_codecs(), EncryptionCodec("encrypted-1", ENCRYPTED_KEY_1)
        )
    )

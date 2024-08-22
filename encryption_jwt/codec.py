from typing import Iterable, List
from temporalio.api.common.v1 import Payload
from temporalio.converter import PayloadCodec
from encryption_jwt.encryptor import KMSEncryptor


class EncryptionCodec(PayloadCodec):
    
    def __init__(self, namespace: str):
        self._encryptor = KMSEncryptor(namespace)

    async def encode(self, payloads: Iterable[Payload]) -> List[Payload]:
        # We blindly encode all payloads with the key and set the metadata with the key that was
        # used (base64 encoded).

        def encrypt_payload(p: Payload):
            data, key = self._encryptor.encrypt(p.SerializeToString())
            return Payload(
                metadata={
                    "encoding": b"binary/encrypted",
                    "data_key_encrypted": key,
                },
                data=data,
            )

        return list(map(encrypt_payload, payloads))

    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        def decrypt_payload(p: Payload):
            data_key_encrypted_base64 = p.metadata.get("data_key_encrypted", b"")
            data = self._encryptor.decrypt(data_key_encrypted_base64, p.data)
            return Payload.FromString(data)

        return list(map(decrypt_payload, payloads))

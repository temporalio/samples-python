import os
from typing import Iterable, List
import base64
import logging

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from temporalio import workflow
from temporalio.api.common.v1 import Payload
from temporalio.converter import PayloadCodec

from botocore.exceptions import ClientError

with workflow.unsafe.imports_passed_through():
    import boto3


class EncryptionCodec(PayloadCodec):
    def __init__(self) -> None:
        super().__init__()
        logging.getLogger('boto3').setLevel(logging.CRITICAL)
        logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
        logging.getLogger('botocore').setLevel(logging.CRITICAL)

    async def encode(self, payloads: Iterable[Payload]) -> List[Payload]:
        data_key_encrypted, data_key_plaintext = self.create_data_key(
            os.environ["AWS_KMS_CMK_ARN"])

        if data_key_encrypted is None:
            return False

        # We blindly encode all payloads with the key and set the metadata with the key that was
        # used (base64 encoded).
        return [
            Payload(
                metadata={
                    "encoding": b"binary/encrypted",
                    "data_key_encrypted": base64.b64encode(data_key_encrypted),
                },
                data=self.encrypt(AESGCM(data_key_plaintext),
                                  p.SerializeToString()),
            )
            for p in payloads
        ]

    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        ret: List[Payload] = []
        for p in payloads:
            # Ignore ones w/out our expected encoding
            if p.metadata.get("encoding", b"").decode() != "binary/encrypted":
                ret.append(p)
                continue

            data_key_encrypted_base64 = p.metadata.get(
                "data_key_encrypted", b"")
            data_key_encrypted = base64.b64decode(data_key_encrypted_base64)
            data_key_plaintext = self.decrypt_data_key(data_key_encrypted)

            if data_key_plaintext is None:
                return False

            # Decrypt and append
            ret.append(Payload.FromString(self.decrypt(
                AESGCM(data_key_plaintext), p.data)))
        return ret

    def create_data_key(self, cmk_id, key_spec='AES_256'):
        """create_data_key description TODO"""

        # Create data key
        kms_client = boto3.client('kms')
        try:
            response = kms_client.generate_data_key(
                KeyId=cmk_id, KeySpec=key_spec)
        except ClientError as e:
            logging.error(e)
            return None, None

        # Return the encrypted and plaintext data key
        return response['CiphertextBlob'], response['Plaintext']

    def encrypt(self, encryptor: AESGCM, data: bytes) -> bytes:
        """encrypt description TODO"""
        nonce = os.urandom(12)
        return nonce + encryptor.encrypt(nonce, data, None)

    def decrypt(self, encryptor: AESGCM, data: bytes) -> bytes:
        """decrypt description TODO"""
        return encryptor.decrypt(data[:12], data[12:], None)

    def decrypt_data_key(self, data_key_encrypted):
        """decrypt_data_key description TODO"""

        # Decrypt the data key
        kms_client = boto3.client('kms')
        try:
            response = kms_client.decrypt(CiphertextBlob=data_key_encrypted)
        except ClientError as e:
            logging.error(e)
            return None

        return response['Plaintext']

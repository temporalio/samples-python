import asyncio
import base64
import logging
import os

from botocore.exceptions import ClientError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import aioboto3


class KMSEncryptor:
    """Encrypts and decrypts using keys from AWS KMS."""

    def __init__(self, namespace: str):
        self._namespace = namespace
        self._boto_session = None

    @property
    def boto_session(self):
        """Get a KMS client from boto3."""
        if not self._boto_session:
            session = aioboto3.Session()
            self._boto_session = session

        return self._boto_session

    async def encrypt(self, data: bytes) -> tuple[bytes, bytes]:
        """Encrypt data using a key from KMS."""
        # The keys are rotated automatically by KMS, so fetch a new key to encrypt the data.
        data_key_encrypted, data_key_plaintext = await self.__create_data_key(
            self._namespace
        )

        if data_key_encrypted is None:
            raise ValueError("No data key!")

        nonce = os.urandom(12)
        encryptor = AESGCM(data_key_plaintext)
        encrypted = asyncio.get_running_loop().run_in_executor(
            None, encryptor.encrypt, nonce, data, None
        )
        return nonce + await encrypted, base64.b64encode(data_key_encrypted)

    async def decrypt(self, data_key_encrypted_base64, data: bytes) -> bytes:
        """Encrypt data using a key from KMS."""
        data_key_encrypted = base64.b64decode(data_key_encrypted_base64)
        data_key_plaintext = await self.__decrypt_data_key(data_key_encrypted)
        encryptor = AESGCM(data_key_plaintext)
        decrypted = await asyncio.get_running_loop().run_in_executor(
            None, encryptor.decrypt, data[:12], data[12:], None
        )
        return decrypted

    async def __create_data_key(self, namespace: str):
        """Get a set of keys from AWS KMS that can be used to encrypt data."""

        # Create data key
        alias_name = "alias/" + namespace.replace(".", "_")
        async with self.boto_session.client("kms") as kms_client:
            response = await kms_client.describe_key(KeyId=alias_name)
            cmk_id = response["KeyMetadata"]["Arn"]
            key_spec = "AES_256"
            try:
                response = await kms_client.generate_data_key(
                    KeyId=cmk_id, KeySpec=key_spec
                )
            except ClientError as e:
                logging.error(e)
                return None, None

            # Return the encrypted and plaintext data key
            return response["CiphertextBlob"], response["Plaintext"]

    async def __decrypt_data_key(self, data_key_encrypted):
        """Use AWS KMS to exchange an encrypted key for its plaintext value."""

        async with self.boto_session.client("kms") as kms_client:
            # Decrypt the data key
            try:
                response = await kms_client.decrypt(CiphertextBlob=data_key_encrypted)
            except ClientError as e:
                logging.error(e)
                return None

            return response["Plaintext"]

import os
import base64
import logging
from temporalio import workflow
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from botocore.exceptions import ClientError

with workflow.unsafe.imports_passed_through():
    import boto3


class KMSEncryptor:
    """Encrypts and decrypts using keys from AWS KMS."""

    def __init__(self):
        self._kms_client = None

    @property
    def kms_client(self):
        """Get a KMS client from boto3."""
        if not self._kms_client:
            self._kms_client = boto3.client("kms")

        return self._kms_client

    def encrypt(self, data: bytes) -> tuple[bytes, bytes]:
        """Encrypt data using a key from KMS."""
        # The keys are rotated automatically by KMS, so fetch a new key to encrypt the data.
        data_key_encrypted, data_key_plaintext = self.__create_data_key()

        if data_key_encrypted is None:
            raise ValueError("No data key!")

        nonce = os.urandom(12)
        encryptor = AESGCM(data_key_plaintext)
        return nonce + encryptor.encrypt(nonce, data, None), base64.b64encode(
            data_key_encrypted
        )

    def decrypt(self, data_key_encrypted_base64, data: bytes) -> bytes:
        """Encrypt data using a key from KMS."""
        data_key_encrypted = base64.b64decode(data_key_encrypted_base64)
        data_key_plaintext = self.__decrypt_data_key(data_key_encrypted)
        encryptor = AESGCM(data_key_plaintext)
        return encryptor.decrypt(data[:12], data[12:], None)

    def __create_data_key(self):
        """Get a set of keys from AWS KMS that can be used to encrypt data."""

        # Create data key
        cmk_id = os.environ["AWS_KMS_CMK_ARN"]
        key_spec = "AES_256"
        try:
            response = self.kms_client.generate_data_key(KeyId=cmk_id, KeySpec=key_spec)
        except ClientError as e:
            logging.error(e)
            return None, None

        # Return the encrypted and plaintext data key
        return response["CiphertextBlob"], response["Plaintext"]

    def __decrypt_data_key(self, data_key_encrypted):
        """Use AWS KMS to exchange an encrypted key for its plaintext value."""

        # Decrypt the data key
        try:
            response = self.kms_client.decrypt(CiphertextBlob=data_key_encrypted)
        except ClientError as e:
            logging.error(e)
            return None

        return response["Plaintext"]

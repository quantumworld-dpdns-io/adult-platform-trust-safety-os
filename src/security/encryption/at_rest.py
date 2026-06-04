import os
import secrets
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AES256GCM:
    def __init__(self, key: Optional[bytes] = None):
        self._key = key or self.generate_key()
        self._aesgcm = AESGCM(self._key)

    @staticmethod
    def generate_key() -> bytes:
        return secrets.token_bytes(32)

    def rotate_key(self, new_key: Optional[bytes] = None) -> bytes:
        old_key = self._key
        self._key = new_key or self.generate_key()
        self._aesgcm = AESGCM(self._key)
        return old_key

    def encrypt_data(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        nonce = secrets.token_bytes(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext

    def decrypt_data(self, data: bytes, associated_data: Optional[bytes] = None) -> bytes:
        nonce = data[:12]
        ciphertext = data[12:]
        return self._aesgcm.decrypt(nonce, ciphertext, associated_data)

    def encrypt_file(self, input_path: str, output_path: str) -> str:
        with open(input_path, "rb") as f:
            plaintext = f.read()
        encrypted = self.encrypt_data(plaintext)
        with open(output_path, "wb") as f:
            f.write(encrypted)
        return output_path

    def decrypt_file(self, input_path: str, output_path: str) -> str:
        with open(input_path, "rb") as f:
            data = f.read()
        plaintext = self.decrypt_data(data)
        with open(output_path, "wb") as f:
            f.write(plaintext)
        return output_path


def generate_key() -> bytes:
    return AES256GCM.generate_key()


def encrypt_file(input_path: str, output_path: str, key: bytes) -> str:
    cipher = AES256GCM(key)
    return cipher.encrypt_file(input_path, output_path)


def decrypt_file(input_path: str, output_path: str, key: bytes) -> str:
    cipher = AES256GCM(key)
    return cipher.decrypt_file(input_path, output_path)


def encrypt_data(data: bytes, key: bytes, associated_data: Optional[bytes] = None) -> bytes:
    cipher = AES256GCM(key)
    return cipher.encrypt_data(data, associated_data)


def decrypt_data(data: bytes, key: bytes, associated_data: Optional[bytes] = None) -> bytes:
    cipher = AES256GCM(key)
    return cipher.decrypt_data(data, associated_data)


def rotate_key(old_key: bytes, new_key: Optional[bytes] = None) -> bytes:
    cipher = AES256GCM(old_key)
    return cipher.rotate_key(new_key)

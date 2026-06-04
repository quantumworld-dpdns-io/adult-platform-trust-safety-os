"""Tests for AES-256-GCM encryption and key generation."""

from __future__ import annotations

import os

import pytest

from src.security.encryption.at_rest import (
    AES256GCM,
    decrypt_data,
    encrypt_data,
    generate_key,
    rotate_key,
)


def test_aes_encrypt_decrypt():
    cipher = AES256GCM()
    plaintext = b"Hello, World! This is sensitive data."
    ciphertext = cipher.encrypt_data(plaintext)
    assert ciphertext != plaintext
    decrypted = cipher.decrypt_data(ciphertext)
    assert decrypted == plaintext


def test_aes_encrypt_decrypt_with_aad():
    cipher = AES256GCM()
    plaintext = b"Authenticated data"
    aad = b"additional-context"
    ciphertext = cipher.encrypt_data(plaintext, associated_data=aad)
    decrypted = cipher.decrypt_data(ciphertext, associated_data=aad)
    assert decrypted == plaintext


def test_aes_wrong_aad_fails():
    cipher = AES256GCM()
    plaintext = b"Protected data"
    ciphertext = cipher.encrypt_data(plaintext, associated_data=b"correct-context")
    with pytest.raises(Exception):
        cipher.decrypt_data(ciphertext, associated_data=b"wrong-context")


def test_generate_key():
    key = generate_key()
    assert isinstance(key, bytes)
    assert len(key) == 32


def test_generate_unique_keys():
    keys = {generate_key() for _ in range(10)}
    assert len(keys) == 10


def test_aes_key_rotation():
    cipher = AES256GCM()
    plaintext = b"Data before rotation"
    ciphertext = cipher.encrypt_data(plaintext)
    old_key = cipher.rotate_key()
    assert len(old_key) == 32
    with pytest.raises(Exception):
        cipher.decrypt_data(ciphertext)


def test_aes_rotate_with_specific_key():
    cipher = AES256GCM()
    new_key = os.urandom(32)
    old_key = cipher.rotate_key(new_key)
    assert old_key is not None
    plaintext = b"New key data"
    ciphertext = cipher.encrypt_data(plaintext)
    decrypted = cipher.decrypt_data(ciphertext)
    assert decrypted == plaintext


def test_encrypt_decrypt_function():
    key = generate_key()
    plaintext = b"Function-level encryption"
    ciphertext = encrypt_data(plaintext, key)
    decrypted = decrypt_data(ciphertext, key)
    assert decrypted == plaintext


def test_rotate_key_function():
    old_key = generate_key()
    new_key = generate_key()
    returned_old = rotate_key(old_key, new_key)
    assert returned_old == old_key


def test_aes_empty_plaintext():
    cipher = AES256GCM()
    ciphertext = cipher.encrypt_data(b"")
    decrypted = cipher.decrypt_data(ciphertext)
    assert decrypted == b""


def test_aes_large_data():
    cipher = AES256GCM()
    plaintext = os.urandom(1024 * 1024)
    ciphertext = cipher.encrypt_data(plaintext)
    decrypted = cipher.decrypt_data(ciphertext)
    assert decrypted == plaintext


def test_aes_file_encrypt_decrypt(tmp_path):
    cipher = AES256GCM()
    input_file = tmp_path / "input.txt"
    encrypted_file = tmp_path / "encrypted.bin"
    decrypted_file = tmp_path / "decrypted.txt"
    input_file.write_bytes(b"File content to encrypt")
    cipher.encrypt_file(str(input_file), str(encrypted_file))
    cipher.decrypt_file(str(encrypted_file), str(decrypted_file))
    assert decrypted_file.read_bytes() == b"File content to encrypt"

import pytest

from app.core import security


def test_password_hash_roundtrip():
    hashed = security.hash_password("hunter2hunter2")
    assert hashed != "hunter2hunter2"
    assert security.verify_password("hunter2hunter2", hashed)
    assert not security.verify_password("wrong-password", hashed)


def test_jwt_roundtrip():
    token = security.create_access_token("42")
    payload = security.decode_access_token(token)
    assert payload["sub"] == "42"


def test_expired_jwt_rejected():
    import jwt

    token = security.create_access_token("42", expires_minutes=-5)
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(token)


def test_token_cipher_roundtrip():
    cipher = security.TokenCipher()
    encrypted = cipher.encrypt("glpat-secret-token")
    assert encrypted != "glpat-secret-token"
    assert cipher.decrypt(encrypted) == "glpat-secret-token"


def test_token_cipher_rejects_tampered():
    cipher = security.TokenCipher()
    with pytest.raises(ValueError):
        cipher.decrypt("not-a-valid-ciphertext")

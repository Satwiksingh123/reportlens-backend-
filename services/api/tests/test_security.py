"""Password hashing and JWT round-trip.

These exist because user registration was completely broken at runtime while the unit
tests passed: passlib 1.7.4 (unmaintained) raises on bcrypt >= 4.1 during its backend
self-test, so every /api/auth/register call 500'd. Nothing covered the hashing path.
"""

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_roundtrip():
    hashed = hash_password("secret12345")
    assert hashed != "secret12345"
    assert verify_password("secret12345", hashed) is True


def test_wrong_password_rejected():
    assert verify_password("nope", hash_password("secret12345")) is False


def test_same_password_hashes_differently():
    # distinct salts per hash
    assert hash_password("samepass") != hash_password("samepass")


def test_long_password_does_not_crash():
    # bcrypt refuses inputs over 72 bytes; we truncate rather than error out.
    long_pw = "a" * 500
    assert verify_password(long_pw, hash_password(long_pw)) is True


def test_multibyte_password_truncated_on_bytes_not_characters():
    # A character-based limit would let a multi-byte password exceed bcrypt's 72-BYTE cap.
    pw = "पासवर्ड" * 40
    assert verify_password(pw, hash_password(pw)) is True


def test_malformed_stored_hash_is_a_failed_login_not_an_error():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_jwt_roundtrip():
    token = create_access_token("user@example.com")
    assert decode_access_token(token) == "user@example.com"


def test_tampered_jwt_rejected():
    token = create_access_token("user@example.com")
    assert decode_access_token(token + "x") is None

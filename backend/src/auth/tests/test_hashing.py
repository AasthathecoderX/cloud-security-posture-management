"""
Tests for M1 password hashing.
"""

from auth.hashing import hash_password, verify_password


def test_password_is_not_stored_as_plaintext():
    password = "CorrectHorseBatteryStaple123!"

    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2")


def test_correct_password_verifies():
    password = "CorrectHorseBatteryStaple123!"

    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_wrong_password_does_not_verify():
    password = "CorrectHorseBatteryStaple123!"

    password_hash = hash_password(password)

    assert verify_password("WrongPassword123!", password_hash) is False


def test_same_password_gets_different_hashes():
    password = "CorrectHorseBatteryStaple123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash

    assert verify_password(password, first_hash) is True
    assert verify_password(password, second_hash) is True


def test_empty_password_fails_verification():
    password_hash = hash_password("ValidPassword123!")

    assert verify_password("", password_hash) is False
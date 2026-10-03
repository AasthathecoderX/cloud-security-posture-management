"""
Password hashing utilities.

M1 authentication uses Argon2id through pwdlib.

Passwords are never stored in plaintext and are never logged.
"""

from pwdlib import PasswordHash


# PasswordHash.recommended() currently selects a secure Argon2id configuration.
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using Argon2id.

    Args:
        password: The plaintext password supplied by the user.

    Returns:
        A salted Argon2id password hash.
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against an Argon2id hash.

    Args:
        password: The plaintext password supplied by the user.
        password_hash: The stored Argon2id hash.

    Returns:
        True when the password matches; otherwise False.
    """
    if not password or not password_hash:
        return False

    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        # Treat malformed/unusable hashes as authentication failure.
        # Do not expose hashing implementation details to the caller.
        return False
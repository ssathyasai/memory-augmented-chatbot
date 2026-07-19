"""Password hashing and security utilities.

Process Flow:
1. Preprocesses plain text passwords using SHA-256 digest to safely handle bcrypt's 72-byte limit.
2. Generates random salt and hashes password bytes using bcrypt.
3. Verifies provided plaintext passwords against stored bcrypt hash strings.
"""

import hashlib
import bcrypt


def _preprocess_password(password: str) -> bytes:
    """
    Preprocess password to handle bcrypt's 72-byte limit.
    Hashes password with SHA-256 first to get a fixed-size input.
    
    Args:
        password: Plain text password
    
    Returns:
        Preprocessed password bytes
    """
    # Encode password to bytes
    password_bytes = password.encode("utf-8")
    # Hash with SHA-256 to get a fixed-size input (32 bytes)
    return hashlib.sha256(password_bytes).digest()


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt (with SHA-256 preprocessing for long passwords).
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    processed = _preprocess_password(password)
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(processed, salt)
    # Return as string
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against
    
    Returns:
        True if password matches, False otherwise
    """
    processed = _preprocess_password(plain_password)
    # Verify
    return bcrypt.checkpw(processed, hashed_password.encode("utf-8"))

import hashlib
import os

PBKDF2_ITERATIONS = 100_000
SALT_LENGTH = 16


def generate_salt() -> str:
    """Generate random salt (16 bytes, hex encoded to 32 chars)."""
    return os.urandom(SALT_LENGTH).hex()


def hash_password(password: str, salt: str) -> str:
    """使用 PBKDF2-HMAC-SHA256 计算密码哈希"""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """验证密码是否匹配哈希"""
    return hash_password(password, salt) == password_hash

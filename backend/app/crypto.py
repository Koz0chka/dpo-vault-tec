"""
Криптография приложения.

Все хэши и ключи строятся на argon2id — это единый алгоритм, как и
требовалось в задании ("ВСЁ ЗАХЭШИРОВАНО ЧЕРЕЗ argon").

Два разных применения argon2:
1. password_hash(master_password, salt) → строка для проверки при логине
2. derive_key(master_password, salt)    → 32-байтовый ключ для Fernet,
                                          которым шифруются сами пароли

Важно: ключ шифрования НЕ хранится в БД. Он выводится «на лету»
из мастер-пароля при логине и держится в оперативной памяти сервера
в словаре сессий. После перезапуска бэкенда пользователям нужно
перелогиниться — это допустимая цена за то, что сервер не хранит
ключ в открытом виде.
"""
from __future__ import annotations

import base64
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from argon2.low_level import hash_secret_raw, Type
from cryptography.fernet import Fernet

from .config import settings


# --- Параметры argon2 (одинаковые для хэша и для KDF) -----------------------
_time_cost = settings.argon2_time_cost
_memory_cost = settings.argon2_memory_cost
_parallelism = settings.argon2_parallelism
_hash_len = settings.argon2_hash_len
_salt_len = settings.argon2_salt_len

# PasswordHasher — для проверки мастер-пароля (хэш хранится как строка).
_hasher = PasswordHasher(
    time_cost=_time_cost,
    memory_cost=_memory_cost,
    parallelism=_parallelism,
    hash_len=_hash_len,
    salt_len=_salt_len,
    type=Type.ID,
)


# --- Утилиты ---------------------------------------------------------------

def generate_salt() -> str:
    """Случайная соль для каждого пользователя. Хранится в БД открыто."""
    return secrets.token_hex(_salt_len)


def hash_master_password(master_password: str, salt_hex: str) -> str:
    """Хэширует мастер-пароль через argon2id.

    Используется PasswordHasher (соль генерируется внутри), а
    переданная соль используется ТОЛЬКО для derive_key — но для
    совместимости мы возвращаем также хэш, который можно проверить.
    """
    return _hasher.hash(master_password)


def verify_master_password(stored_hash: str, master_password: str) -> bool:
    """Проверка мастер-пароля против сохранённого argon2-хэша."""
    try:
        return _hasher.verify(stored_hash, master_password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def derive_fernet_key(master_password: str, salt_hex: str) -> bytes:
    """Выводит 32-байтовый ключ для Fernet из мастер-пароля.

    argon2id используется здесь как KDF: hash_secret_raw возвращает
    «сырые» байты заданной длины. Base64-кодируем их — Fernet ждёт
    urlsafe-base64 ключ.
    """
    salt_bytes = bytes.fromhex(salt_hex)
    raw = hash_secret_raw(
        secret=master_password.encode("utf-8"),
        salt=salt_bytes,
        time_cost=_time_cost,
        memory_cost=_memory_cost,
        parallelism=_parallelism,
        hash_len=settings.fernet_key_len,
        type=Type.ID,
    )
    return base64.urlsafe_b64encode(raw)


def encrypt_value(plaintext: str, fernet_key: bytes) -> str:
    """Шифрует пароль перед сохранением в БД."""
    return Fernet(fernet_key).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str, fernet_key: bytes) -> str:
    """Расшифровывает пароль при показе пользователю."""
    return Fernet(fernet_key).decrypt(ciphertext.encode("utf-8")).decode("utf-8")

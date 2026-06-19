"""
Сессии: JWT-токены и in-memory хранилище ключей шифрования.

После успешного логина сервер выводит ключ шифрования паролей из
мастер-пароля и держит его в памяти, привязав к id пользователя.
Сам JWT не содержит ключа — он только идентифицирует пользователя.

При перезапуске бэкенда ключи теряются — пользователям нужно
перелогиниться. Это компромисс между безопасностью (ключ не на диске)
и удобством.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from .config import settings


_lock = threading.Lock()
# user_id -> bytes (Fernet key)
_keys: dict[int, bytes] = {}


def issue_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


def store_key(user_id: int, fernet_key: bytes) -> None:
    with _lock:
        _keys[user_id] = fernet_key


def get_key(user_id: int) -> Optional[bytes]:
    with _lock:
        return _keys.get(user_id)


def drop_key(user_id: int) -> None:
    with _lock:
        _keys.pop(user_id, None)

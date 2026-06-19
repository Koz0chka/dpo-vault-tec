"""
Зависимости FastAPI: извлечение текущего пользователя из JWT.

`get_current_user` возвращает id и username.
`require_session_key` дополнительно гарантирует, что в памяти сервера
есть ключ шифрования для этого пользователя (т.е. он выполнил логин
в текущем жизненном цикле процесса).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from .sessions import get_key, verify_token


@dataclass(frozen=True)
class CurrentUser:
    id: int
    username: str


def _extract_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется заголовок Authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный формат заголовка Authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parts[1]


def get_current_user(authorization: Optional[str] = Header(default=None)) -> CurrentUser:
    token = _extract_token(authorization)
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истёкший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return CurrentUser(id=int(payload["sub"]), username=payload["username"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_session_key(user: CurrentUser = Depends(get_current_user)) -> tuple[CurrentUser, bytes]:
    """Возвращает (user, fernet_key) или 401, если ключа в памяти нет."""
    key = get_key(user.id)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия устарела — войдите снова",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user, key

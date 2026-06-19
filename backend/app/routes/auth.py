"""Маршруты регистрации и входа."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ..crypto import (
    derive_fernet_key,
    generate_salt,
    hash_master_password,
    verify_master_password,
)
from ..database import get_conn
from ..deps import CurrentUser, get_current_user
from ..schemas import LoginRequest, RegisterRequest, TokenResponse
from ..sessions import drop_key, issue_token, store_key


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest) -> TokenResponse:
    """Регистрация нового пользователя.

    Мастер-пароль хэшируется argon2id; отдельная соль используется
    для вывода ключа шифрования через argon2-KDF.
    """
    salt_hex = generate_salt()
    pwd_hash = hash_master_password(body.master_password, salt_hex)

    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (body.username, pwd_hash, salt_hex),
            )
            user_id = int(cur.lastrowid)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким именем уже существует",
            )

    # Сразу выдадим токен и положим ключ в память — пользователь залогинен.
    fernet_key = derive_fernet_key(body.master_password, salt_hex)
    store_key(user_id, fernet_key)
    token = issue_token(user_id, body.username)
    return TokenResponse(access_token=token, username=body.username)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, salt FROM users WHERE username = ?",
            (body.username,),
        ).fetchone()

    if row is None:
        # Одинаковое сообщение для «нет пользователя» и «неверный пароль» —
        # чтобы не раскрывать факт существования аккаунта.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )

    if not verify_master_password(row["password_hash"], body.master_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )

    fernet_key = derive_fernet_key(body.master_password, row["salt"])
    store_key(int(row["id"]), fernet_key)
    token = issue_token(int(row["id"]), row["username"])
    return TokenResponse(access_token=token, username=row["username"])


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: CurrentUser = Depends(get_current_user)) -> Response:
    drop_key(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

"""Маршруты работы с паролями пользователя: CRUD + генерация."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ..crypto import decrypt_value, encrypt_value
from ..database import get_conn
from ..deps import CurrentUser, require_session_key
from ..password_gen import PasswordPolicy, estimate_strength, generate_password
from ..schemas import (
    GeneratePasswordRequest,
    GeneratePasswordResponse,
    PasswordCreateRequest,
    PasswordEntry,
    PasswordListItem,
    PasswordRenameRequest,
    PasswordUpdateValueRequest,
)


router = APIRouter(prefix="/api/passwords", tags=["passwords"])


@router.get("", response_model=list[PasswordListItem])
def list_passwords(deps: tuple[CurrentUser, bytes] = Depends(require_session_key)):
    user, _ = deps
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, created_at, updated_at FROM passwords "
            "WHERE user_id = ? ORDER BY updated_at DESC",
            (user.id,),
        ).fetchall()
    return [PasswordListItem(**dict(r)) for r in rows]


@router.post("", response_model=PasswordEntry, status_code=status.HTTP_201_CREATED)
def create_password(
    body: PasswordCreateRequest,
    deps: tuple[CurrentUser, bytes] = Depends(require_session_key),
):
    user, key = deps
    enc = encrypt_value(body.value, key)
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO passwords (user_id, name, encrypted_value) VALUES (?, ?, ?)",
                (user.id, body.name, enc),
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Запись с таким именем уже существует",
            )
        row = conn.execute(
            "SELECT id, name, created_at, updated_at FROM passwords WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return PasswordEntry(
        id=row["id"],
        name=row["name"],
        value=body.value,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{entry_id}", response_model=PasswordEntry)
def get_password(
    entry_id: int,
    deps: tuple[CurrentUser, bytes] = Depends(require_session_key),
):
    user, key = deps
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, encrypted_value, created_at, updated_at "
            "FROM passwords WHERE id = ? AND user_id = ?",
            (entry_id, user.id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    plaintext = decrypt_value(row["encrypted_value"], key)
    return PasswordEntry(
        id=row["id"],
        name=row["name"],
        value=plaintext,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.patch("/{entry_id}/name", response_model=PasswordListItem)
def rename_password(
    entry_id: int,
    body: PasswordRenameRequest,
    deps: tuple[CurrentUser, bytes] = Depends(require_session_key),
):
    user, _ = deps
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM passwords WHERE id = ? AND user_id = ?",
            (entry_id, user.id),
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
        try:
            conn.execute(
                "UPDATE passwords SET name = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND user_id = ?",
                (body.new_name, entry_id, user.id),
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Запись с таким именем уже существует",
            )
        row = conn.execute(
            "SELECT id, name, created_at, updated_at FROM passwords WHERE id = ?",
            (entry_id,),
        ).fetchone()
    return PasswordListItem(**dict(row))


@router.patch("/{entry_id}/value", response_model=PasswordListItem)
def update_password_value(
    entry_id: int,
    body: PasswordUpdateValueRequest,
    deps: tuple[CurrentUser, bytes] = Depends(require_session_key),
):
    user, key = deps
    enc = encrypt_value(body.new_value, key)
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE passwords SET encrypted_value = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND user_id = ?",
            (enc, entry_id, user.id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
        row = conn.execute(
            "SELECT id, name, created_at, updated_at FROM passwords WHERE id = ?",
            (entry_id,),
        ).fetchone()
    return PasswordListItem(**dict(row))


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_password(
    entry_id: int,
    deps: tuple[CurrentUser, bytes] = Depends(require_session_key),
) -> Response:
    user, _ = deps
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM passwords WHERE id = ? AND user_id = ?",
            (entry_id, user.id),
        )
    if cur.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Генератор паролей -----------------------------------------------------

@router.post("/generate", response_model=GeneratePasswordResponse)
def generate(
    body: GeneratePasswordRequest,
    _deps: tuple[CurrentUser, bytes] = Depends(require_session_key),
):
    """Генерация пароля по заданной политике.

    Эндпоинт требует аутентификации, чтобы им не могли пользоваться
    анонимы. Сам сгенерированный пароль НЕ сохраняется — пользователь
    решает, сохранить его или скопировать.
    """
    policy = PasswordPolicy(
        length=body.length,
        use_lower=body.use_lower,
        use_upper=body.use_upper,
        use_digits=body.use_digits,
        use_symbols=body.use_symbols,
        avoid_ambiguous=body.avoid_ambiguous,
    )
    try:
        pwd = generate_password(policy)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return GeneratePasswordResponse(password=pwd, strength=estimate_strength(pwd))

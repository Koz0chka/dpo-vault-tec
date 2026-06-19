"""
Инициализация SQLite-базы данных.

Схема:
- users:      хранит мастер-пароль (argon2id hash) и метаданные аккаунта
- passwords:  хранит пароли пользователя в зашифрованном виде
              (Fernet с ключом, выведенным из мастер-пароля через argon2 KDF)

ALL hashes use argon2id — текущий рекомендованный OWASP алгоритм.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS passwords (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    name            TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_passwords_user_id ON passwords(user_id);
"""


def _ensure_db_dir() -> None:
    db_dir = os.path.dirname(settings.db_path)
    if db_dir and not os.path.isdir(db_dir):
        os.makedirs(db_dir, exist_ok=True)


def init_db() -> None:
    """Создаёт файл БД и таблицы, если их ещё нет."""
    _ensure_db_dir()
    with sqlite3.connect(settings.db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Контекстный менеджер для соединения с БД.

    Включает PRAGMA foreign_keys=ON, чтобы ON DELETE CASCADE работал.
    """
    conn = sqlite3.connect(settings.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

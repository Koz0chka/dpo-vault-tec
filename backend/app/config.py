"""
Конфигурация приложения.
Секреты загружаются из переменных окружения, что позволяет
безопасно хранить их вне кода (в docker-compose / .env).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Секрет для подписи JWT-токенов. В проде задаётся через env.
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production-please")
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = int(os.getenv("JWT_TTL_MINUTES", "120"))

    # Путь к файлу SQLite. По умолчанию — внутри контейнера, но
    # монтируется как volume в docker-compose, чтобы данные не терялись.
    db_path: str = os.getenv("DB_PATH", "/data/passwords.db")

    # Параметры Argon2id. Значения по умолчанию рекомендованы OWASP.
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536        # 64 МБ
    argon2_parallelism: int = 4
    argon2_hash_len: int = 32
    argon2_salt_len: int = 16

    # Длина ключа шифрования Fernet (в байтах после base64 — 32).
    fernet_key_len: int = 32

    # CORS: фронтенд и бэкенд в разных контейнерах, поэтому разрешаем
    # конкретный origin. Через Caddy запросы идут через один домен,
    # но для разработки оставляем поддержку отдельного origin.
    cors_origins: tuple[str, ...] = (
        "https://test.kozochka.org",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    )


settings = Settings()

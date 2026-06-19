"""
Точка входа FastAPI.

Запуск в проде:  uvicorn app.main:app --host 0.0.0.0 --port 8000
                 (статика раздаётся Caddy из ../frontend)

Запуск локально: SERVE_STATIC=1 uvicorn app.main:app --reload --port 8000
                 (FastAPI сам раздаёт фронтенд из ../frontend на том же порту,
                  Caddy не нужен — один URL, никаких проблем с CORS)

В контейнере порт 8000; наружу пробрасывается через Caddy.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routes import auth, passwords


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("vaulttec")


app = FastAPI(
    title="Vault-Tec Password Vault API",
    version="1.0.0",
    description="Веб-помощник для контроля доступа: генератор и шифрованный архив паролей.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def _on_startup() -> None:
    init_db()
    log.info("SQLite initialized at %s", settings.db_path)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(passwords.router)


# ---------------------------------------------------------------------------
# Dev-режим: раздаём фронтенд из ../frontend на том же порту, что и API.
# В проде этим занимается Caddy — там SERVE_STATIC не ставим.
# ---------------------------------------------------------------------------

SERVE_STATIC = os.getenv("SERVE_STATIC", "").lower() in ("1", "true", "yes")

if SERVE_STATIC:
    # Путь к frontend/ относительно backend/app/main.py
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    if not frontend_dir.is_dir():
        log.warning("SERVE_STATIC=1, but frontend dir not found at %s", frontend_dir)
    else:
        # Статические ассеты (css, js, favicon)
        app.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
        app.mount("/js",  StaticFiles(directory=frontend_dir / "js"),  name="js")
        app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets-root")

        # Отдельные HTML-страницы отдаются явно, чтобы /api/* не перехватывались.
        @app.get("/", include_in_schema=False)
        async def _index():
            return FileResponse(frontend_dir / "index.html")

        @app.get("/register.html", include_in_schema=False)
        async def _register():
            return FileResponse(frontend_dir / "register.html")

        @app.get("/dashboard.html", include_in_schema=False)
        async def _dashboard():
            return FileResponse(frontend_dir / "dashboard.html")

        @app.get("/favicon.svg", include_in_schema=False)
        async def _favicon():
            return FileResponse(frontend_dir / "favicon.svg")

        log.info("DEV mode: serving frontend from %s on the same port", frontend_dir)

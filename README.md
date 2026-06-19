# Vault-Tec Password Vault

**Веб-помощник для контроля доступа: генератор и шифрованный архив паролей.**
Интерфейс в эстетике Fallout / Pip-Boy: моноширинный фосфорно-зелёный терминал
RobCo Industries, CRT-скан-линии, терминальные орнаменты.

Бэкенд: Python (FastAPI), SQLite, всё хэшируется / выводится ключ через **argon2id**.
Фронтенд: чистые HTML/CSS/JS без фреймворков.
Развёртывание: два Docker-контейнера (backend + Caddy), Caddy светится
на домене `hermenius.kozochka.org` и автоматически получает TLS-сертификат
от Let's Encrypt.

---

## Возможности

- Регистрация и вход по мастер-паролю.
- Мастер-пароль хэшируется **argon2id** (рекомендованные OWASP параметры).
- Сами сохранённые пароли шифруются **Fernet**; ключ выводится из
  мастер-пароля через **argon2id-KDF**. В БД хранятся только
  зашифрованные значения.
- Генератор паролей с настраиваемой длиной и наборами символов.
- CRUD по сохранённым паролям: создать, переименовать, изменить значение,
  удалить.
- Поиск по названиям, показ/скрытие значения, копирование в буфер.
- JWT-авторизация, CORS, заголовки безопасности, CSP в Caddy.
- Pip-Boy стилистика: скан-линии, моноширинный шрифт, amber-предупреждения.

---

## Структура проекта

```
.
├── backend/                # FastAPI + SQLite + argon2
│   ├── app/
│   │   ├── main.py         # точка входа FastAPI
│   │   ├── config.py       # настройки (env)
│   │   ├── database.py     # SQLite: схема, миграции, соединения
│   │   ├── crypto.py       # argon2id: хэш + KDF; Fernet шифрование
│   │   ├── sessions.py     # JWT + in-memory хранилище ключей
│   │   ├── deps.py         # Depends: текущий пользователь, ключ сессии
│   │   ├── password_gen.py # генератор паролей
│   │   ├── schemas.py      # Pydantic-модели
│   │   └── routes/
│   │       ├── auth.py     # /api/auth/{register,login,logout}
│   │       └── passwords.py# /api/passwords + /generate
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # статичный фронтенд (тема Pip-Boy)
│   ├── index.html          # вход
│   ├── register.html       # регистрация
│   ├── dashboard.html      # хранилище
│   ├── favicon.svg
│   ├── css/style.css
│   └── js/
│       ├── api.js          # обёртка над fetch + токены
│       ├── auth.js         # логика страницы входа
│       ├── register.js     # логика регистрации + оценка силы
│       └── dashboard.js    # логика хранилища
├── caddy/
│   ├── Caddyfile           # прод: hermenius.kozochka.org + TLS + headers
│   └── dev.Caddyfile       # локально: http://localhost:8080 без TLS
├── docker-compose.yml      # 2 контейнера: backend + caddy
├── .env.example            # шаблон переменных окружения
└── README.md
```

## Архитектура безопасности

### Мастер-пароль
- Хэшируется `argon2id` через `PasswordHasher` из `argon2-cffi`
  (параметры: time_cost=3, memory_cost=64 МБ, parallelism=4).
- Хранится в таблице `users.password_hash`.

### Ключ шифрования паролей
- Выводится из мастер-пароля через `argon2id` как KDF
  (`hash_secret_raw`, тот же набор параметров, hash_len=32).
- Используется как ключ для `cryptography.fernet.Fernet`.
- В БД **не хранится**. После успешного логина ключ держится
  в оперативной памяти процесса бэкенда. После перезапуска процесса
  пользователям нужно войти заново.

### Хранимые пароли
- В таблице `passwords.encrypted_value` лежит строка
  `Fernet.encrypt(plaintext)`. Без мастер-пароля её не расшифровать.

### Авторизация
- После логина/регистрации выдаётся JWT (`HS256`) с TTL 2 часа.
- Токен хранится в `localStorage` и шлётся в заголовке
  `Authorization: Bearer <token>`.

### Сетевая безопасность
- Backend контейнер не пробрасывает порт наружу — ходить можно
  только через Caddy.
- Caddy автоматически получает TLS-сертификат Let's Encrypt.
- Включены HSTS, CSP, X-Frame-Options: DENY, X-Content-Type-Options.

---

## API — краткая справка

Все маршруты под `/api`.

| Метод   | Путь                          | Описание                              | Авторизация |
|---------|-------------------------------|---------------------------------------|-------------|
| GET     | `/api/health`                 | Healthcheck                           | —           |
| POST    | `/api/auth/register`          | Регистрация                           | —           |
| POST    | `/api/auth/login`             | Вход                                  | —           |
| POST    | `/api/auth/logout`            | Выход                                 | Bearer      |
| GET     | `/api/passwords`              | Список (без расшифровки)              | Bearer      |
| POST    | `/api/passwords`              | Создать                               | Bearer      |
| GET     | `/api/passwords/{id}`         | Показать (с расшифровкой)             | Bearer      |
| PATCH   | `/api/passwords/{id}/name`    | Переименовать                         | Bearer      |
| PATCH   | `/api/passwords/{id}/value`   | Изменить пароль                       | Bearer      |
| DELETE  | `/api/passwords/{id}`         | Удалить                               | Bearer      |
| POST    | `/api/passwords/generate`     | Сгенерировать пароль (не сохраняется) | Bearer      |

---

## Используемые технологии

- **Бэкенд:** Python 3.12+ (включая 3.14), FastAPI, uvicorn
- **Криптография:** argon2-cffi (argon2id), cryptography (Fernet), python-jose (JWT)
- **БД:** SQLite (стандартная библиотека `sqlite3`)
- **Фронтенд:** HTML5, CSS3 (без препроцессоров), ванильный JS (ES2020)
- **Шрифты:** Share Tech Mono + VT323 (Google Fonts)
- **Развёртывание:** Docker, Docker Compose v2, Caddy 2.8

---

## Лицензия

Учебный проект. Используйте свободно. Vault-Tec and RobCo Industries
are trademarks of their respective owners — used here purely for
thematic flavor.

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

---

## Локальный запуск (самый простой способ)

### Вариант A — один uvicorn (САМЫЙ ПРОСТОЙ, без Caddy)

FastAPI умеет раздавать и API, и статику фронтенда на одном порту.
Включается переменной окружения `SERVE_STATIC=1`. Никакого Caddy,
никаких проблем с CORS, никакого второго терминала.

```bash
cd Vault-Tec
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

export JWT_SECRET="dev-$(openssl rand -hex 16)"
export DB_PATH="/tmp/vaulttec-dev.db"
export SERVE_STATIC=1
rm -f "$DB_PATH"

uvicorn backend.app.main:app --reload --port 8000
```

Открыть: **http://localhost:8000** — увидишь зелёный терминал Vault-Tec.
Swagger UI на **http://localhost:8000/docs**.

`SERVE_STATIC=1` нужно использовать **только локально**. В проде
статикой занимается Caddy, а контейнер бэкенда эту переменную не ставит.

### Вариант B — uvicorn + Caddy dev (если Caddy уже стоит)

Это способ, максимально близкий к прод-конфигурации: Caddy раздаёт
фронтенд и проксирует API на uvicorn, всё на одном порту.

**1. Установить зависимости Python:**

```bash
cd Vault-Tec
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

**2. Установить Caddy (Arch Linux):**

```bash
sudo pacman -S caddy
# Если 404 на зеркалах — сначала:
# sudo pacman -Syy caddy
```

**3. В двух терминалах запустить бэкенд и фронтенд-прокси:**

Терминал 1 (бэкенд):
```bash
cd Vault-Tec
source .venv/bin/activate
export JWT_SECRET="dev-$(openssl rand -hex 16)"
export DB_PATH="/tmp/vaulttec-dev.db"
rm -f "$DB_PATH"
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Терминал 2 (Caddy-прокси):
```bash
cd Vault-Tec
caddy run --config caddy/dev.Caddyfile --adapter caddyfile
```

Открыть: **http://localhost:8080**

### Вариант C — только uvicorn (для отладки API без фронтенда)

Если нужно потыкать эндпоинты через Swagger UI без фронтенда:

```bash
cd Vault-Tec
source .venv/bin/activate
export JWT_SECRET="dev-$(openssl rand -hex 16)"
export DB_PATH="/tmp/vaulttec-dev.db"
uvicorn backend.app.main:app --reload --port 8000
```

Открыть: **http://localhost:8000/docs** — интерактивная документация
с всеми эндпоинтами, можно дёргать прямо оттуда.

---

## Развёртывание на сервере (hermenius.kozochka.org)

### 1. Подготовка сервера

На сервере должны быть:
- Docker ≥ 24
- Docker Compose v2 (`docker compose`)
- Открытые порты 80 и 443

### 2. DNS

Добавьте A-запись:

```
hermenius.kozochka.org.   IN  A   <IP-вашего-сервера>
```

Дождитесь расклейки (`dig hermenius.kozochka.org`).

### 3. Клонирование и настройка

```bash
git clone <repo> Vault-Tec
cd Vault-Tec
cp .env.example .env

# Сгенерируйте секрет JWT
openssl rand -base64 48
# И впишите его в .env вместо плейсхолдера
```

Пример `.env`:
```
JWT_SECRET=K9hM2sL...сгенерированная-строка...
JWT_TTL_MINUTES=120
```

### 4. Сборка и запуск

```bash
docker compose up -d --build
```

Caddy при первом старте запросит сертификат у Let's Encrypt
и в течение ~30 секунд поднимет HTTPS.

Проверка:
```bash
docker compose ps
curl -s https://hermenius.kozochka.org/api/health
# -> {"status":"ok"}
```

Откройте в браузере: **https://hermenius.kozochka.org**

### 5. Логи

```bash
docker compose logs -f caddy
docker compose logs -f backend
```

### 6. Обновление

```bash
git pull
docker compose up -d --build
```

### 7. Резервное копирование

БД лежит в volume `backend-data`:
```bash
docker compose exec backend sqlite3 /data/passwords.db .dump > backup.sql
```

---

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

Фреймворки на фронтенде **не используются** — как и требовалось в задании.

---

## Лицензия

Учебный проект. Используйте свободно. Vault-Tec and RobCo Industries
are trademarks of their respective owners — used here purely for
thematic flavor.

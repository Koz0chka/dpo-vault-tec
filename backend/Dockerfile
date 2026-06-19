FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Системные библиотеки, нужные argon2-cffi и cryptography.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Каталог для SQLite-файла. Монтируется как volume в docker-compose.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# uvicorn запускается с 1 воркером, потому что ключи шифрования хранятся
# в памяти процесса (in-memory session store). При нескольких воркерах
# ключи не будут разделены между ними.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

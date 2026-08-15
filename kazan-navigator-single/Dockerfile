# ============================================================
# Казань Навигатор 4.0 — Dockerfile
# ============================================================
FROM python:3.12-slim

# Системные зависимости для osmium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1-dev \
    zlib1g-dev \
    libbz2-dev \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаём директорию для данных
RUN mkdir -p static/data

# Порт
EXPOSE 5000

# Переменные окружения
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Запуск через gunicorn (production)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]

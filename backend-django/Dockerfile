# backend-django/Dockerfile
FROM python:3.12-slim

# Установка gettext
RUN apt-get update && \
    apt-get install -y --no-install-recommends gettext libgettextpo-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y curl

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY src/ .

# Порт
EXPOSE 8000

# Команда по умолчанию
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
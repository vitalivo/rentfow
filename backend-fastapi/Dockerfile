FROM python:3.12-slim

# --- ИСПРАВЛЕНО (3): Установлена рабочая директория /app ---
# Это стандартная практика и соответствует вашему 'volumes' в docker-compose
WORKDIR /app

# Копируем requirements.txt (из ./backend-fastapi) в /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y curl

# Копируем код из ./backend-fastapi/src в /app
# Это необходимо для сборки, даже если 'volumes' перекроет это при разработке
COPY src/ src/

EXPOSE 8001

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]

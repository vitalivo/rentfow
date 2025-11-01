#!/bin.sh

# 1. Запуск gRPC-сервера в фоновом режиме
python src/main_grpc.py &

# 2. Запуск HTTP/FastAPI сервера в основном процессе
# --reload здесь оставлен для удобства разработки
exec uvicorn src.main_http:app --host 0.0.0.0 --port 8001 --reload
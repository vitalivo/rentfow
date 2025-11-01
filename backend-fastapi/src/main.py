# backend-fastapi/src/main.py
import asyncio
import logging
from threading import Thread

from fastapi import FastAPI
from grpc_server.lease_service import serve as start_grpc_server

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fastapi')

app = FastAPI(title="RentFlow FastAPI Service")

@app.on_event("startup")
async def startup_event():
    """Действия при старте приложения"""
    logger.info("Starting up FastAPI application...")
    
    # Запускаем gRPC-сервер в отдельном потоке
    grpc_thread = Thread(target=lambda: asyncio.run(start_grpc_server()), daemon=True)
    grpc_thread.start()
    logger.info("gRPC server thread started")

@app.get("/")
def read_root():
    return {"message": "FastAPI is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/grpc-test")
def grpc_test():
    """Эндпоинт для тестирования gRPC-сервера"""
    return {
        "status": "ok",
        "grpc_server": "running",
        "port": 50051
    }
    
if __name__ == "__main__":
    import uvicorn
    # Запускаем Uvicorn, который в свою очередь вызовет startup_event
    # и запустит gRPC-сервер в отдельном потоке
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)    
# backend-fastapi/src/grpc_server/lease_service.py
import asyncio
import logging
from concurrent import futures

import sys
import os
import grpc

if '/rentflow_protos' not in sys.path:
    sys.path.insert(0, '/rentflow_protos') 
    
from rentflow_protos import rentflow_pb2
from rentflow_protos import rentflow_pb2_grpc

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('grpc_server')

class LeaseService(rentflow_pb2_grpc.LeaseServiceServicer):
    """Реализация gRPC-сервиса для управления арендой"""
    
    def __init__(self):
        logger.info("LeaseService initialized")
        super().__init__()
    
    def CreateLease(self, request, context):
        """Создание нового договора аренды"""
        logger.info(f"Received CreateLease request: {request}")
        
        # Здесь будет логика сохранения в базу данных
        # Для теста просто возвращаем успешный ответ
        response = rentflow_pb2.CreateLeaseResponse(
            success=True,
            message="Lease created successfully",
            lease=rentflow_pb2.Lease(
                id=1,
                property=request.property,
                tenant=request.tenant,
                start_date=request.start_date,
                end_date=request.end_date,
                monthly_rent=request.monthly_rent,
                payment_day=request.payment_day
            )
        )
        return response
    
    def GetLease(self, request, context):
        """Получение информации о договоре аренды"""
        logger.info(f"Received GetLease request for lease_id={request.lease_id}")
        
        # Здесь будет логика получения из базы данных
        # Для теста возвращаем фиктивные данные
        response = rentflow_pb2.GetLeaseResponse(
            found=True,
            lease=rentflow_pb2.Lease(
                id=request.lease_id,
                property=rentflow_pb2.Property(
                    address="ул. Ленина, 15",
                    city="Москва",
                    country="Россия"
                ),
                tenant=rentflow_pb2.Tenant(
                    first_name="Иван",
                    last_name="Иванов",
                    email="ivan@example.com"
                ),
                start_date="2025-01-01",
                end_date="2025-12-31",
                monthly_rent=50000.0,
                payment_day=1
            )
        )
        return response

async def serve():
    """Запуск gRPC-сервера"""
    server = grpc.aio.server()
    
    # Добавляем реализацию сервиса
    rentflow_pb2_grpc.add_LeaseServiceServicer_to_server(LeaseService(), server)
    
    # Настраиваем порт (50051 - стандартный порт gRPC)
    server.add_insecure_port('[::]:50051')
    
    logger.info("Starting gRPC server on port 50051...")
    await server.start()
    
    # Ждем завершения работы
    await server.wait_for_termination()

if __name__ == '__main__':
    # Запуск в синхронном режиме для отладки
    asyncio.run(serve())
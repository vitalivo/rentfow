# backend-fastapi/src/grpc_server/lease_service.py

import asyncio
import logging
from concurrent import futures
import sys
import os
import grpc
import json 
from datetime import datetime

# --- ИМПОРТ И ИНИЦИАЛИЗАЦИЯ KAFKA ---
try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError

    # Получаем адрес Kafka из переменных окружения (задан в docker-compose)
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPIC = "lease_events" 
    
    # Инициализация Producer. Работает в потоке ThreadPoolExecutor gRPC-сервера.
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=5, # Добавим небольшой ретрай
        # Синхронный режим, подходит для использования в gRPC ThreadPoolExecutor
    )
    logger = logging.getLogger('grpc_server')
    logger.info(f"Kafka Producer initialized for servers: {KAFKA_BOOTSTRAP_SERVERS}")
    
except ImportError:
    logger.critical("KafkaProducer not found. Ensure 'kafka-python' is installed.")
    producer = None
except Exception as e:
    logger.critical(f"FATAL: Error initializing Kafka Producer: {e}")
    producer = None
# -------------------------------------

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

# ----------------------------------------------------------------------
# --- ФУНКЦИЯ ОТПРАВКИ В KAFKA ---
# ----------------------------------------------------------------------

def publish_lease_created_event(event_data: dict):
    """
    Отправляет сообщение о создании аренды в Kafka.
    """
    if producer:
        try:
            # Отправка сообщения
            future = producer.send(KAFKA_TOPIC, event_data)
            producer.flush() # Блокирует до завершения всех отправленных сообщений
            
            # Опционально: можно проверить, что сообщение действительно доставлено
            record_metadata = future.get(timeout=10)
            logger.info(f"KAFKA SENT: LeaseCreated event delivered to topic '{record_metadata.topic}' partition {record_metadata.partition} offset {record_metadata.offset}")
            
        except KafkaError as e:
            logger.error(f"KAFKA ERROR: Failed to send message to Kafka: {e}")
        except Exception as e:
            logger.error(f"KAFKA ERROR: Unexpected error during send: {e}")
    else:
        logger.warning("KAFKA WARNING: Producer is not initialized. Skipping actual send.")


# ----------------------------------------------------------------------
# --- РЕАЛИЗАЦИЯ СЕРВИСА ---
# ----------------------------------------------------------------------

class LeaseService(rentflow_pb2_grpc.LeaseServiceServicer):
    
    def __init__(self):
        logger.info("LeaseService initialized")
        super().__init__()
    
    def CreateLease(self, request, context):
        
        django_lease_id = request.django_lease_id
        logger.info(f"Received CreateLease request for Django ID: {django_lease_id}")
        
        try:
            # 1. СИМУЛЯЦИЯ СОХРАНЕНИЯ (пока без БД)
            # В реальном проекте, FastAPI получит свой уникальный ID после сохранения
            fastapi_lease_id = django_lease_id + 1000 # Имитируем уникальность ID
            
            # 2. Подготовка данных для Kafka
            event_data = {
                "event_type": "LeaseCreated",
                "fastapi_id": fastapi_lease_id,
                "django_id": django_lease_id,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "start_date": request.start_date,
                    "monthly_rent": request.monthly_rent,
                    "tenant_email": request.tenant.email,
                    # В реальном коде, мы бы добавили больше данных об аренде, 
                    # полученных из локальной БД FastAPI, после сохранения.
                }
            }
            
            # 3. Публикация в Kafka
            publish_lease_created_event(event_data)
            
            # 4. Формирование успешного ответа
            response_lease = rentflow_pb2.Lease(
                id=fastapi_lease_id, # Возвращаем ID FastAPI, который Django сохранит как fastapi_id
                start_date=request.start_date,
                monthly_rent=request.monthly_rent,
            )

            response = rentflow_pb2.CreateLeaseResponse(
                success=True,
                message="Lease created successfully",
                lease=response_lease
            )
            
            logger.info(f"Successfully processed and sent Kafka event for Django ID: {django_lease_id}. FastAPI ID: {fastapi_lease_id}")
            return response
        
        except Exception as e:
            logger.error(f"Error processing CreateLease for Django ID {django_lease_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal processing error: {e}")
            
            return rentflow_pb2.CreateLeaseResponse(
                success=False,
                message=f"Processing failed: {e}"
            )
            
    # --- Остальные методы ---
    
    def GetLease(self, request, context):
        """Получение информации о договоре аренды (ЗАГЛУШКА)"""
        logger.info(f"Received GetLease request for lease_id={request.lease_id}")
        
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
    # Используем ThreadPoolExecutor для синхронного Kafka Producer
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10)) 
    rentflow_pb2_grpc.add_LeaseServiceServicer_to_server(LeaseService(), server)
    server.add_insecure_port('[::]:50051')
    logger.info("Starting gRPC server on port 50051...")
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())
    
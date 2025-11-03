import asyncio
import logging
from concurrent import futures
import sys
import os
import grpc
import json 
from datetime import datetime
from decimal import Decimal

# --- ИМПОРТ И ИНИЦИАЛИЗАЦИЯ KAFKA ---

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('grpc_server')

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError

    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPIC = "lease_events" 
    
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=5,
    )
    logger.info(f"Kafka Producer initialized for servers: {KAFKA_BOOTSTRAP_SERVERS}")
    
except ImportError:
    logger.critical("KafkaProducer not found. Ensure 'kafka-python' is installed.")
    producer = None
except Exception as e:
    logger.error(f"Kafka initialization error: {e}")
    producer = None


# --- ИМПОРТ PROTOS ---
if '/rentflow_protos' not in sys.path:
    # Важно: путь должен соответствовать тому, где находятся сгенерированные файлы
    sys.path.insert(0, '/rentflow_protos') 
    
from rentflow_protos import rentflow_pb2
from rentflow_protos import rentflow_pb2_grpc

# --- ИМИТАЦИЯ ГЕНЕРАЦИИ ID ---
# Продолжаем с последнего успешного ID
lease_id_counter = 1008 

# ----------------------------------------------------------------------
# --- ФУНКЦИЯ ОТПРАВКИ В KAFKA ---
# ----------------------------------------------------------------------

def publish_lease_event(event_data: dict, topic: str = KAFKA_TOPIC):
    """
    Отправляет любое сообщение в Kafka.
    """
    if producer:
        try:
            future = producer.send(topic, event_data)
            producer.flush()
            record_metadata = future.get(timeout=10)
            logger.info(f"KAFKA SENT: {event_data['event_type']} event delivered to topic '{record_metadata.topic}' partition {record_metadata.partition} offset {record_metadata.offset}")
            return True
        except KafkaError as e:
            logger.error(f"KAFKA ERROR: Failed to send message to Kafka: {e}")
            return False
        except Exception as e:
            logger.error(f"KAFKA ERROR: Unexpected error during send: {e}")
            return False
    else:
        logger.warning("KAFKA WARNING: Producer is not initialized. Skipping actual send.")
        return False


# ----------------------------------------------------------------------
# --- РЕАЛИЗАЦИЯ СЕРВИСА ---
# ----------------------------------------------------------------------

class LeaseService(rentflow_pb2_grpc.LeaseServiceServicer):
    
    def __init__(self):
        logger.info("LeaseService initialized")
        super().__init__()
    
    # ====================================================================
    # 1. CREATE LEASE (БЕЗ ИЗМЕНЕНИЙ, Т.К. MESSAGE ТАМ ЕСТЬ)
    # ====================================================================
    def CreateLease(self, request, context):
        global lease_id_counter
        
        # 1. СИМУЛЯЦИЯ СОХРАНЕНИЯ и генерация ID
        lease_id_counter += 1
        fastapi_lease_id = lease_id_counter
        django_lease_id = request.django_lease_id 
        
        logger.info(f"Received CreateLease request for Django ID: {django_lease_id}. Assigning FastAPI ID: {fastapi_lease_id}")
        
        try:
            # 2. Подготовка и публикация данных для Kafka
            event_data = {
                "event_type": "LeaseCreated",
                "fastapi_id": fastapi_lease_id,
                "django_id": django_lease_id,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "start_date": request.start_date,
                    "monthly_rent": request.monthly_rent,
                    "tenant_email": request.tenant.email,
                }
            }
            
            publish_success = publish_lease_event(event_data)
            
            if not publish_success:
                 raise Exception("Не удалось опубликовать событие LeaseCreated в Kafka.")
            
            # 3. Формирование успешного ответа
            response_lease = rentflow_pb2.Lease(
                id=fastapi_lease_id,
                start_date=request.start_date,
                monthly_rent=request.monthly_rent,
            )

            logger.info(f"Successfully processed and sent Kafka event for Django ID: {django_lease_id}. FastAPI ID: {fastapi_lease_id}")
            return rentflow_pb2.CreateLeaseResponse(
                success=True,
                message="Lease created, Kafka event published.",
                lease=response_lease
            )
        
        except Exception as e:
            logger.error(f"Error processing CreateLease for Django ID {django_lease_id}: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal processing error: {e}")
            return rentflow_pb2.CreateLeaseResponse(
                success=False,
                message=f"Processing failed: {e}"
            )

    # ====================================================================
    # 2. UPDATE LEASE (ИСПРАВЛЕНО: УДАЛЕНО ПОЛЕ 'MESSAGE')
    # ====================================================================
    def UpdateLease(self, request, context):
        fastapi_id = request.lease_id 
        
        logger.info(f"Received UpdateLease request for FastAPI ID: {fastapi_id}")

        try:
            # 1. Подготовка данных для Kafka
            details = {}
            
            if request.HasField('monthly_rent'):
                details['monthly_rent'] = request.monthly_rent

            if request.HasField('end_date') and request.end_date:
                details['end_date'] = request.end_date
            
            if not details:
                logger.warning(f"UpdateLease request for ID {fastapi_id} contained no fields to update.")
                return rentflow_pb2.UpdateLeaseResponse(
                    success=False,
                    # message="Нет данных для обновления.", # <-- УДАЛЕНО!
                )

            django_id = 8 
            
            event_data = {
                "event_type": "LeaseUpdated",
                "fastapi_id": fastapi_id,
                "django_id": django_id,
                "timestamp": datetime.now().isoformat(),
                "details": details
            }
            
            publish_success = publish_lease_event(event_data)
            
            if not publish_success:
                 raise Exception("Не удалось опубликовать событие LeaseUpdated в Kafka.")

            # 2. Формирование успешного ответа
            response_lease = rentflow_pb2.Lease(id=fastapi_id) 

            logger.info(f"Successfully processed UpdateLease. Kafka event LeaseUpdated sent for Django ID: {django_id}.")
            return rentflow_pb2.UpdateLeaseResponse(
                success=True,
                # message="Lease updated, Kafka event published.", # <-- УДАЛЕНО!
                lease=response_lease
            )
        
        except Exception as e:
            logger.error(f"Error processing UpdateLease for FastAPI ID {fastapi_id}: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal processing error: {e}")
            return rentflow_pb2.UpdateLeaseResponse(
                success=False,
                # message=f"Processing failed: {e}" # <-- УДАЛЕНО!
            )

    # ====================================================================
    # 3. TERMINATE LEASE (ИСПРАВЛЕНО: УДАЛЕНО ПОЛЕ 'MESSAGE')
    # ====================================================================
    def TerminateLease(self, request, context):
        fastapi_id = request.fastapi_lease_id 
        actual_end_date = request.actual_end_date
        
        logger.info(f"Received TerminateLease request for FastAPI ID: {fastapi_id}. Actual End Date: {actual_end_date}")

        try:
            # 1. Подготовка данных для Kafka
            django_id = 8 # Используем тестовый ID Django
            
            event_data = {
                "event_type": "LeaseTerminated",
                "fastapi_id": fastapi_id,
                "django_id": django_id,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "actual_end_date": actual_end_date
                }
            }
            
            publish_success = publish_lease_event(event_data)
            
            if not publish_success:
                 raise Exception("Не удалось опубликовать событие LeaseTerminated в Kafka.")

            logger.info(f"Successfully processed TerminateLease. Kafka event LeaseTerminated sent for Django ID: {django_id}.")
            return rentflow_pb2.TerminateLeaseResponse(
                success=True,
                # message="Lease terminated, Kafka event published.", # <-- УДАЛЕНО!
            )
        
        except Exception as e:
            logger.error(f"Error processing TerminateLease for FastAPI ID {fastapi_id}: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal processing error: {e}")
            return rentflow_pb2.TerminateLeaseResponse(
                success=False,
                # message=f"Processing failed: {e}" # <-- УДАЛЕНО!
            )
            
# --- Запуск сервера (остается прежним) ---
async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10)) 
    rentflow_pb2_grpc.add_LeaseServiceServicer_to_server(LeaseService(), server)
    server.add_insecure_port('[::]:50051')
    logger.info("Starting gRPC server on port 50051...")
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())
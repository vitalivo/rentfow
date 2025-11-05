# backend-django/leases/grpc_client.py

import grpc
import logging
from typing import Dict, Any
from datetime import date # <-- Импорт date должен быть здесь
from datetime import datetime
# --- СТАНДАРТНЫЙ ИМПОРТ ---
try:
    import rentflow_pb2
    import rentflow_pb2_grpc
except ImportError:
    logging.critical("CRITICAL: Не удалось импортировать 'rentflow_pb2'.")
    logging.critical("Убедитесь, что PYTHONPATH в docker-compose.yml настроен верно.")
    raise

# Настраиваем логгер для этого модуля
import os


logger = logging.getLogger(__name__)

# Получаем адрес gRPC-сервера из настроек Django (или переменных окружения)
GRPC_SERVER_ADDRESS = os.environ.get("GRPC_SERVER_ADDRESS", "fastapi-tracking:50051")

# Кастомные ошибки
class GRPCConnectionError(Exception):
    """Ошибка подключения к gRPC-серверу."""
    pass

class GRPCRequestError(Exception):
    """Ошибка при обработке gRPC-запроса на стороне сервера."""
    pass

def _get_stub():
    """Создает и возвращает gRPC-стаб."""
    try:
        # Используем insecure_channel, так как сервисы находятся в одной Docker-сети
        channel = grpc.insecure_channel(GRPC_SERVER_ADDRESS)
        # Проверяем доступность канала
        grpc.channel_ready_future(channel).result(timeout=5)
        return rentflow_pb2_grpc.LeaseServiceStub(channel)
    except grpc.FutureTimeoutError as e:
        logger.error(f"gRPC Connection Timeout: {e}")
        raise GRPCConnectionError(f"Не удалось подключиться к gRPC-серверу по адресу {GRPC_SERVER_ADDRESS}")
    except Exception as e:
        logger.error(f"gRPC Connection Error: {e}")
        raise GRPCConnectionError(f"Ошибка подключения к gRPC-серверу: {e}")


def send_create_lease_request(property_data, tenant_data, lease_details, django_lease_id):
    """Отправляет запрос на создание новой аренды."""
    stub = _get_stub()
    
    # Заполнение protobuf-сообщения
    request = rentflow_pb2.CreateLeaseRequest(
        django_lease_id=django_lease_id,  # Ключевой ID для обратной связи
        property=rentflow_pb2.Property(**property_data),
        tenant=rentflow_pb2.Tenant(**tenant_data),
        start_date=lease_details['start_date'].strftime('%Y-%m-%d'),
        end_date=lease_details['end_date'].strftime('%Y-%m-%d'),
        monthly_rent=float(lease_details['monthly_rent']),
        payment_day=lease_details['payment_day'],
    )
    
    try:
        response = stub.CreateLease(request)
        return response
    except grpc.RpcError as e:
        logger.error(f"gRPC RPC Error in CreateLease: {e}")
        raise GRPCRequestError(f"Ошибка gRPC при создании аренды: {e.details()}")
    
# ----------------------------------------------------------------------
# --- НОВЫЕ МЕТОДЫ ОБНОВЛЕНИЯ И ЗАВЕРШЕНИЯ ---
# ----------------------------------------------------------------------

def send_update_lease_request(fastapi_lease_id: int, django_lease_id: int, update_fields: dict):
    """Отправляет запрос на обновление существующей аренды."""
    stub = _get_stub()
    
    # 1. Формируем основной запрос
    request_kwargs = {
        'lease_id': int(fastapi_lease_id), # В вашем proto ID назван 'lease_id'
        # Мы не можем отправить django_lease_id, т.к. его нет в UpdateLeaseRequest
        # Мы можем добавить его в .proto, но пока обойдемся без него для теста.
    }

    # Добавляем опциональные поля только если они есть в update_fields
    if 'monthly_rent' in update_fields:
        # Убедитесь, что передаете float (proto использует float)
        request_kwargs['monthly_rent'] = float(update_fields['monthly_rent']) 

    if 'end_date' in update_fields:
        # Убедитесь, что передаете строку YYYY-MM-DD
        request_kwargs['end_date'] = update_fields['end_date'].strftime('%Y-%m-%d')
    
    request = rentflow_pb2.UpdateLeaseRequest(**request_kwargs)
    
    try:
        response = stub.UpdateLease(request)
        return response
    except grpc.RpcError as e:
        logger.error(f"gRPC RPC Error in UpdateLease: {e}")
        raise GRPCRequestError(f"Ошибка gRPC при обновлении аренды: {e.details()}")



def send_terminate_lease_request(fastapi_lease_id: int, django_lease_id: int, actual_end_date: str):
    """Отправляет запрос на завершение (терминацию) аренды."""
    stub = _get_stub()
    
    request = rentflow_pb2.TerminateLeaseRequest(
        fastapi_lease_id=int(fastapi_lease_id),
        django_lease_id=django_lease_id,
        actual_end_date=actual_end_date.strftime('%Y-%m-%d') # Дата должна быть в формате 'YYYY-MM-DD'
    )
    
    try:
        response = stub.TerminateLease(request)
        return response
    except grpc.RpcError as e:
        logger.error(f"gRPC RPC Error in TerminateLease: {e}")
        raise GRPCRequestError(f"Ошибка gRPC при завершении аренды: {e.details()}")
    
    
    
# ====================================================================
# Добавьте этот код для ТЕСТИРОВАНИЯ
# ====================================================================
# Вам понадобится импортировать KafkaProducer
from kafka import KafkaProducer
import json
import os

# Инициализация тестового Producer (должно быть глобальным)
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
TEST_PRODUCER = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_test_event(event_type, django_id, fastapi_id, details=None):
    """
    Отправляет произвольное тестовое событие в топик Kafka.
    Используется только для отладки Consumer.
    """
    event = {
        'event_type': event_type,
        'django_id': django_id,
        'fastapi_id': fastapi_id,
        'timestamp': datetime.now().isoformat(),
        'details': details or {}
    }
    try:
        TEST_PRODUCER.send('lease_events', event)
        TEST_PRODUCER.flush() # Немедленно отправить сообщение
        print(f"✅ TEST PRODUCER: Sent {event_type} for Django ID {django_id} to Kafka.")
        return True
    except Exception as e:
        print(f"❌ TEST PRODUCER Error: {e}")
        return False
# ====================================================================   
    
    
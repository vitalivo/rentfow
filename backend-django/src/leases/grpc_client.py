# backend-django/leases/grpc_client.py

import grpc
import logging
from typing import Dict, Any
from datetime import date, datetime
import os
import json
from kafka import KafkaProducer

# --- Импорт protobuf ---
try:
    import rentflow_pb2
    import rentflow_pb2_grpc
except ImportError:
    logging.critical("CRITICAL: Не удалось импортировать 'rentflow_pb2'.")
    logging.critical("Убедитесь, что PYTHONPATH в docker-compose.yml настроен верно.")
    raise

logger = logging.getLogger(__name__)

# Адрес gRPC-сервера
GRPC_SERVER_ADDRESS = os.environ.get("GRPC_SERVER_ADDRESS", "fastapi-tracking:50051")

# Кастомные ошибки
class GRPCConnectionError(Exception):
    """Ошибка подключения к gRPC-серверу."""
    pass

class GRPCRequestError(Exception):
    """Ошибка при обработке gRPC-запроса на стороне сервера."""
    pass

# ----------------------------------------------------------------------
# gRPC stub (ленивая инициализация)
# ----------------------------------------------------------------------
_GRPC_STUB = None

def _get_stub():
    """Создает и возвращает gRPC-стаб (лениво)."""
    global _GRPC_STUB
    if _GRPC_STUB is None:
        try:
            channel = grpc.insecure_channel(GRPC_SERVER_ADDRESS)
            grpc.channel_ready_future(channel).result(timeout=5)
            _GRPC_STUB = rentflow_pb2_grpc.LeaseServiceStub(channel)
            logger.info("✅ gRPC stub initialized")
        except grpc.FutureTimeoutError as e:
            logger.error(f"gRPC Connection Timeout: {e}")
            raise GRPCConnectionError(f"Не удалось подключиться к gRPC-серверу по адресу {GRPC_SERVER_ADDRESS}")
        except Exception as e:
            logger.error(f"gRPC Connection Error: {e}")
            raise GRPCConnectionError(f"Ошибка подключения к gRPC-серверу: {e}")
    return _GRPC_STUB

# ----------------------------------------------------------------------
# Методы работы с gRPC
# ----------------------------------------------------------------------
def send_create_lease_request(property_data, tenant_data, lease_details, django_lease_id):
    stub = _get_stub()
    request = rentflow_pb2.CreateLeaseRequest(
        django_lease_id=django_lease_id,
        property=rentflow_pb2.Property(**property_data),
        tenant=rentflow_pb2.Tenant(**tenant_data),
        start_date=lease_details['start_date'].strftime('%Y-%m-%d'),
        end_date=lease_details['end_date'].strftime('%Y-%m-%d'),
        monthly_rent=float(lease_details['monthly_rent']),
        payment_day=lease_details['payment_day'],
    )
    try:
        return stub.CreateLease(request)
    except grpc.RpcError as e:
        logger.error(f"gRPC RPC Error in CreateLease: {e}")
        raise GRPCRequestError(f"Ошибка gRPC при создании аренды: {e.details()}")

def send_update_lease_request(fastapi_lease_id: int, django_lease_id: int, update_fields: dict):
    stub = _get_stub()
    request_kwargs = {
        'lease_id': int(fastapi_lease_id),
    }
    if 'monthly_rent' in update_fields:
        request_kwargs['monthly_rent'] = float(update_fields['monthly_rent'])
    if 'end_date' in update_fields:
        request_kwargs['end_date'] = update_fields['end_date'].strftime('%Y-%m-%d')
    request = rentflow_pb2.UpdateLeaseRequest(**request_kwargs)
    try:
        return stub.UpdateLease(request)
    except grpc.RpcError as e:
        logger.error(f"gRPC RPC Error in UpdateLease: {e}")
        raise GRPCRequestError(f"Ошибка gRPC при обновлении аренды: {e.details()}")

def send_terminate_lease_request(fastapi_lease_id: int, django_lease_id: int, actual_end_date: date):
    stub = _get_stub()
    request = rentflow_pb2.TerminateLeaseRequest(
        fastapi_lease_id=int(fastapi_lease_id),
        django_lease_id=django_lease_id,
        actual_end_date=actual_end_date.strftime('%Y-%m-%d')
    )
    try:
        return stub.TerminateLease(request)
    except grpc.RpcError as e:
        logger.error(f"gRPC RPC Error in TerminateLease: {e}")
        raise GRPCRequestError(f"Ошибка gRPC при завершении аренды: {e.details()}")

# ----------------------------------------------------------------------
# Kafka Producer (ленивая инициализация)
# ----------------------------------------------------------------------
_KAFKA_PRODUCER = None
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')

def _get_producer():
    global _KAFKA_PRODUCER
    if _KAFKA_PRODUCER is None:
        try:
            _KAFKA_PRODUCER = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            print("✅ Kafka Producer initialized")
        except Exception as e:
            print(f"❌ Kafka Producer init failed: {e}")
            _KAFKA_PRODUCER = None
    return _KAFKA_PRODUCER

def send_test_event(event_type, django_id, fastapi_id, details=None):
    """Отправляет произвольное тестовое событие в топик Kafka."""
    producer = _get_producer()
    if not producer:
        print("❌ No Kafka Producer available")
        return False

    event = {
        'event_type': event_type,
        'django_id': django_id,
        'fastapi_id': fastapi_id,
        'timestamp': datetime.now().isoformat(),
        'details': details or {}
    }
    try:
        producer.send('lease_events', event)
        producer.flush()
        print(f"✅ TEST PRODUCER: Sent {event_type} for Django ID {django_id} to Kafka.")
        return True
    except Exception as e:
        print(f"❌ TEST PRODUCER Error: {e}")
        return False
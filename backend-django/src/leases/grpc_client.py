# backend-django/leases/grpc_client.py

import grpc
import logging
from typing import Dict, Any
from datetime import date # <-- Импорт date должен быть здесь

# --- СТАНДАРТНЫЙ ИМПОРТ ---
try:
    import rentflow_pb2
    import rentflow_pb2_grpc
except ImportError:
    logging.critical("CRITICAL: Не удалось импортировать 'rentflow_pb2'.")
    logging.critical("Убедитесь, что PYTHONPATH в docker-compose.yml настроен верно.")
    raise

# Настраиваем логгер для этого модуля
logger = logging.getLogger(__name__)

# Адрес сервиса FastAPI из docker-compose.yml
FASTAPI_TARGET_ADDRESS = 'fastapi-tracking:50051'

# --- Кастомные исключения для чистой обработки во views ---

class GRPCConnectionError(Exception):
    """Не удалось установить соединение с gRPC-сервером."""
    pass

class GRPCRequestError(Exception):
    """Ошибка во время выполнения gRPC-запроса (сервер FastAPI вернул ошибку)."""
    pass


def _get_lease_stub():
    """Создает gRPC-стаб для взаимодействия с FastAPI."""
    try:
        channel = grpc.insecure_channel(FASTAPI_TARGET_ADDRESS)
        # Проверяем готовность канала с таймаутом 5 секунд
        grpc.channel_ready_future(channel).result(timeout=5)
        logger.debug(f"gRPC канал к {FASTAPI_TARGET_ADDRESS} готов.")
        return rentflow_pb2_grpc.LeaseServiceStub(channel)
    
    except grpc.FutureTimeoutError:
        logger.error(f"ОШИБКА: Не удалось подключиться к gRPC-серверу {FASTAPI_TARGET_ADDRESS} за 5 сек.")
        raise GRPCConnectionError(f"Сервис отслеживания (FastAPI) недоступен.")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при создании gRPC-канала: {e}")
        raise GRPCConnectionError(str(e))


def send_create_lease_request(
    property_data: Dict[str, Any], 
    tenant_data: Dict[str, Any], 
    lease_details: Dict[str, Any],
    django_lease_id: int # <-- НОВЫЙ АРГУМЕНТ (Шаг 4.3)
) -> rentflow_pb2.CreateLeaseResponse:
    """
    Отправляет gRPC-запрос на создание аренды в сервис FastAPI.
    """
    
    # 1. Получаем stub.
    stub = _get_lease_stub()
    
    # 2. Собираем запрос из словарей (Усиленная защита от ошибок типа)
    try:
        # Безопасное получение значений
        monthly_rent_val = lease_details.get('monthly_rent')
        payment_day_val = lease_details.get('payment_day')
        start_date_obj = lease_details.get('start_date')
        end_date_obj = lease_details.get('end_date')
        
        # Если DRF почему-то пропустил отсутствие обязательных полей
        if monthly_rent_val is None or payment_day_val is None or start_date_obj is None or end_date_obj is None:
            raise ValueError("Отсутствуют обязательные поля аренды.")
            
        # Преобразование datetime.date в строку (YYYY-MM-DD), это мы исправили ранее
        start_date_str = start_date_obj.isoformat()
        end_date_str = end_date_obj.isoformat()
            
        request = rentflow_pb2.CreateLeaseRequest(
            property=rentflow_pb2.Property(
                address=property_data.get('address'),
                city=property_data.get('city'),
                country=property_data.get('country')
            ),
            tenant=rentflow_pb2.Tenant(
                first_name=tenant_data.get('first_name'),
                last_name=tenant_data.get('last_name'),
                email=tenant_data.get('email')
            ),
            
            # НОВОЕ ПОЛЕ: Передаем ID, созданный в Django
            django_lease_id=django_lease_id,
            
            # Строковые поля дат
            start_date=start_date_str,
            end_date=end_date_str,
            
            # Числовые поля
            monthly_rent=float(monthly_rent_val),
            payment_day=int(payment_day_val)
        )
    except Exception as e:
        # Логируем, какие данные вызвали ошибку
        logger.error(f"Ошибка при сборке gRPC-сообщения: {e}. Входные данные: {lease_details}")
        raise ValueError(f"Ошибка данных при создании gRPC-запроса: {e}")

    
    # 3. Выполняем RPC-вызов с обработкой ошибок
    try:
        logger.info("Отправка gRPC-запроса CreateLease в FastAPI...")
        response = stub.CreateLease(request)
        
        if not response.success:
            logger.warning(f"FastAPI вернул ошибку обработки: {response.message}")
        else:
            logger.info(f"FastAPI успешно создал аренду: {response.lease.id}")
            
        return response

    except grpc.RpcError as e:
        logger.error(f"Критическая ошибка gRPC (RpcError) при вызове CreateLease: {e.details()}")
        raise GRPCRequestError(f"Ошибка RPC: {e.details()}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при вызове gRPC: {e}")
        raise GRPCRequestError(f"Непредвиденная ошибка: {e}")
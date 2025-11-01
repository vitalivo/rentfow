import sys
import os
import grpc
import logging
import importlib.util # <--- НОВАЯ БИБЛИОТЕКА ДЛЯ ПРЯМОЙ ЗАГРУЗКИ

# Настройка логирования для чистого вывода
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- ТОЧЕЧНЫЙ ФИКС ИМПОРТА ---
MODULE_PATH = "/rentflow_protos"

def load_module_from_path(module_name, file_name):
    """Загружает модуль напрямую из абсолютного пути."""
    full_path = os.path.join(MODULE_PATH, file_name)
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    if spec is None:
        logging.error(f"Не удалось найти файл протокола: {full_path}")
        sys.exit(1)
        
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

try:
    # Загружаем файлы протоколов напрямую, обходя проблемы с монтированием пакета
    rentflow_pb2 = load_module_from_path("rentflow_pb2", "rentflow_pb2.py")
    rentflow_pb2_grpc = load_module_from_path("rentflow_pb2_grpc", "rentflow_pb2_grpc.py")
    logging.info("Импорт протоколов успешно завершен через importlib.")
except Exception as e:
    logging.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ЗАГРУЗКИ МОДУЛЕЙ: {e}")
    sys.exit(1)
# --- КОНЕЦ ФИКСА ИМПОРТА ---


def create_lease_stub():
    """Создает gRPC-стаб для взаимодействия с FastAPI."""
    
    # 3-секундный таймаут для channel_ready_future
    channel = grpc.insecure_channel('fastapi-tracking:50051')
    
    try:
        # Проверяем доступность соединения (таймаут 5 секунд)
        grpc.channel_ready_future(channel).result(timeout=5)
        logging.info("СОЕДИНЕНИЕ УСПЕШНО УСТАНОВЛЕНО.")
    except grpc.FutureTimeoutError:
        logging.error("ОШИБКА: Не удалось установить соединение с fastapi-tracking:50051 в течение 5 секунд.")
        raise ConnectionRefusedError("gRPC-сервер FastAPI недоступен или не отвечает.")
        
    return rentflow_pb2_grpc.LeaseServiceStub(channel)

def run_test():
    """Запускает полный gRPC-тест."""
    logging.info("--- ЗАПУСК gRPC ТЕСТА СОЕДИНЕНИЯ ---")
    
    # 1. Сначала проверяем, что FastAPI виден и отвечает на 50051
    try:
        stub = create_lease_stub()
    except ConnectionRefusedError as e:
        # Это ожидаемая ошибка, если соединение не установлено
        logging.error(f"Тест провален на этапе соединения: {e}")
        return

    # 2. Если stub создан, отправляем тестовый запрос
    test_property = {'address': "Тестовая улица, 1", 'city': "Тестоград", 'country': "Тестовая страна"}
    test_tenant = {'first_name': "Тест", 'last_name': "Тестов", 'email': "test@example.com"}
    test_lease = {'start_date': "2025-01-01", 'end_date': "2025-12-31", 'monthly_rent': 50000.0, 'payment_day': 1}
    
    try:
        # Используем загруженные модули
        request = rentflow_pb2.CreateLeaseRequest(
            property=rentflow_pb2.Property(**test_property),
            tenant=rentflow_pb2.Tenant(**test_tenant),
            start_date=test_lease['start_date'],
            end_date=test_lease['end_date'],
            monthly_rent=test_lease['monthly_rent'],
            payment_day=test_lease['payment_day']
        )
        
        logging.info("Отправка запроса CreateLease...")
        response = stub.CreateLease(request)
        
        if response.success:
            logging.info("✅ УСПЕХ: gRPC-запрос выполнен успешно!")
            logging.info(f"Ответ FastAPI: {response.message}")
            logging.info(f"ID созданного Lease: {response.lease.id}")
        else:
            logging.error(f"❌ ПРОВАЛ: gRPC-запрос завершился неудачей: {response.message}")

    except grpc.RpcError as e:
        # Это ловит ошибку, если соединение было установлено, но FastAPI упал во время обработки запроса
        logging.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА gRPC (сервер упал при обработке): {e}")
    except Exception as e:
        logging.error(f"❌ НЕПРЕДВИДЕННАЯ ОШИБКА: {e}")


if __name__ == '__main__':
    run_test()
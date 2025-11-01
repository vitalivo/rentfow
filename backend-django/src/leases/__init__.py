# Django: App Initialization File

# Импортируем gRPC-клиенты, чтобы убедиться, что они загружаются
# и доступны внутри пакета leases. 
# Это необходимо для устранения ModuleNotFoundError при первом импорте views.

try:
    from . import grpc_client
except ImportError as e:
    # В этом месте должна быть только ошибка, если файл grpc_clients.py не существует.
    # Если файл существует, но ошибка продолжается, это проблема с PYTHONPATH, но
    # мы ее уже решили ранее, поэтому оставляем только для явного импорта.
    pass

# Определение имени приложения для Django (AppConfig)
# Корректный путь, предполагающий, что leases находится прямо в src/
default_app_config = 'leases.apps.LeasesConfig' 
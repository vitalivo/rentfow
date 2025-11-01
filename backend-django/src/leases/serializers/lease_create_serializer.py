# backend-django/leases/serializers/property_tenant_serializers.py
# Лучше вынести в отдельный файл, так как они используются только здесь.

from rest_framework import serializers

# --- Вложенные Сериализаторы ---

class PropertyCreateSerializer(serializers.Serializer):
    """Сериализатор для данных Property в рамках создания Lease."""
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100)

class TenantCreateSerializer(serializers.Serializer):
    """Сериализатор для данных Tenant в рамках создания Lease."""
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=255)
    # phone не обязателен в gRPC-сообщении, но может быть добавлен
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)


# --- Основной Сериализатор Создания Аренды ---

class LeaseCreateSerializer(serializers.Serializer):
    """
    Основной сериализатор для POST /api/leases/create/.
    Валидирует данные и готовит их к отправке через gRPC.
    """
    # Вложенные объекты, соответствующие структуре gRPC-запроса
    property = PropertyCreateSerializer()
    tenant = TenantCreateSerializer()

    # Поля Lease
    start_date = serializers.DateField(format="%Y-%m-%d")
    end_date = serializers.DateField(format="%Y-%m-%d")
    monthly_rent = serializers.FloatField(min_value=0.01)
    payment_day = serializers.IntegerField(min_value=1, max_value=31)

    def create(self, validated_data):
        """
        В отличие от ModelSerializer, здесь мы не сохраняем данные в БД.
        Мы возвращаем словарь, который будет передан gRPC-клиенту.
        """
        # Эта логика будет реализована в View.
        # Сериализатор просто гарантирует валидацию.
        return validated_data
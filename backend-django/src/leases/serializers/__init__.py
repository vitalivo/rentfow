# leases/serializers/__init__.py
from .property_serializer import PropertySerializer
from .tenant_serializer import TenantSerializer
from .lease_serializer import LeaseSerializer

# Опционально: экспорт всех
__all__ = [
    'PropertySerializer',
    'TenantSerializer',
    'LeaseSerializer'
]
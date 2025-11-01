# leases/serializers/tenant_serializer.py
from rest_framework import serializers
from ..models import Tenant

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'
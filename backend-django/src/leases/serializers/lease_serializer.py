# leases/serializers/lease_serializer.py
from rest_framework import serializers
from ..models import Lease

class LeaseSerializer(serializers.ModelSerializer):
    property = serializers.StringRelatedField()
    tenant = serializers.StringRelatedField()

    class Meta:
        model = Lease
        fields = '__all__'
# leases/serializers/property_serializer.py
from rest_framework import serializers
from ..models import Property

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'  # или перечислите поля: ['id', 'address', 'city', 'country']
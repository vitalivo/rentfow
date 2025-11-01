# leases/views.py
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Property, Tenant, Lease
from .serializers import PropertySerializer, TenantSerializer, LeaseSerializer

@api_view(['GET', 'POST'])
def property_list_create(request):
    if request.method == 'GET':
        properties = Property.objects.all()
        serializer = PropertySerializer(properties, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = PropertySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def tenant_list(request):
    tenants = Tenant.objects.all()
    serializer = TenantSerializer(tenants, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def lease_list(request):
    leases = Lease.objects.select_related('property', 'tenant').all()
    serializer = LeaseSerializer(leases, many=True)
    return Response(serializer.data)

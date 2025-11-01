# leases/views.py

from django.http import JsonResponse
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

# --- ВАЖНО: Модели для сохранения в DB Django ---
from .models import Property, Tenant, Lease 

from .serializers import PropertySerializer, TenantSerializer, LeaseSerializer
from .serializers.lease_create_serializer import LeaseCreateSerializer
from .grpc_client import send_create_lease_request, GRPCConnectionError, GRPCRequestError

logger = logging.getLogger(__name__)

# --- Функции list/create остаются прежними ---

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


# ----------------------------------------------------------------------
# --- ЭНДПОИНТ ДЛЯ СОЗДАНИЯ АРЕНДЫ ЧЕРЕЗ gRPC (С ЛОГИКОЙ DB DJANGO) ---
# ----------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def lease_create_grpc(request):
    """
    1. Валидирует данные.
    2. Сохраняет Lease, Property, Tenant в DB Django.
    3. Отправляет gRPC-запрос с ID нового Lease в FastAPI.
    4. Обновляет Lease в Django, используя ID от FastAPI.
    """
    serializer = LeaseCreateSerializer(data=request.data)
    lease_instance = None 
    
    if serializer.is_valid():
        validated_data = serializer.validated_data
        
        # ----------------------------------------------------
        # БЛОК 1: СОХРАНЕНИЕ МЕТАДАННЫХ В DB DJANGO
        # ----------------------------------------------------
        try:
            # 1. Разделяем данные
            property_data = validated_data.pop('property')
            tenant_data = validated_data.pop('tenant')
            lease_details = validated_data # start_date, monthly_rent и т.д.

            # 2. Создаем Property
            property_instance = Property.objects.create(**property_data)
            
            # 3. Создаем Tenant
            tenant_instance = Tenant.objects.create(**tenant_data)
            
            # 4. Создаем Lease
            lease_instance = Lease.objects.create(
                property=property_instance,
                tenant=tenant_instance,
                **lease_details 
            )
            
            django_lease_id = lease_instance.id
            logger.info(f"Django Lease ID: {django_lease_id} успешно создан в DB.")

        except Exception as e:
            logger.error(f"Ошибка сохранения в DB Django: {e}")
            return Response({"status": "error", "error": "Database Save Error", "details": str(e)}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # ----------------------------------------------------
        # БЛОК 2: ОТПРАВКА gRPC-ЗАПРОСА
        # ----------------------------------------------------
        try:
            # Передаем ID, созданный в Django, в gRPC-клиент
            response_pb = send_create_lease_request(
                property_data=property_data, 
                tenant_data=tenant_data, 
                lease_details=lease_details,
                django_lease_id=django_lease_id # <-- ПЕРЕДАЧА НОВОГО ID
            )

            # 3. Обрабатываем gRPC-ответ
            if response_pb.success:
                # УСПЕХ: Обновляем Lease в Django ID, полученным от FastAPI
                if lease_instance:
                    # Поле fastapi_id должно существовать в модели Lease
                    lease_instance.fastapi_id = response_pb.lease.id 
                    lease_instance.save()
                    logger.info(f"Django Lease ID {django_lease_id} обновлен FastAPI ID: {response_pb.lease.id}")

                response_data = {
                    "status": "success",
                    "message": response_pb.message,
                    "lease_id": django_lease_id, # ID из Django
                    "fastapi_id": response_pb.lease.id, # ID из FastAPI
                    "created_lease_data": {
                        "start_date": response_pb.lease.start_date,
                        "monthly_rent": response_pb.lease.monthly_rent,
                    }
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                # FastAPI обработал, но вернул ошибку логики
                return Response({
                    "status": "failure",
                    "error": "FastAPI Logic Error",
                    "details": response_pb.message
                }, status=status.HTTP_400_BAD_REQUEST)

        except (GRPCConnectionError, GRPCRequestError, Exception) as e:
            # Ошибка gRPC: Желательно удалить запись из DB Django, но оставим для простоты
            error_status = status.HTTP_503_SERVICE_UNAVAILABLE if isinstance(e, GRPCConnectionError) else status.HTTP_500_INTERNAL_SERVER_ERROR
            return Response({
                "status": "error",
                "error": "gRPC Service Error",
                "details": str(e)
            }, status=error_status)
            
    # Ошибка валидации DRF
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# leases/views.py
from django.http import JsonResponse
import logging # <-- ДОБАВЛЕН ИМПОРТ LOGGING
from rest_framework.decorators import api_view, permission_classes # Убедились, что permission_classes импортирован
from rest_framework.permissions import AllowAny # Убедились, что AllowAny импортирован
from rest_framework.response import Response
from rest_framework import status
from .models import Property, Tenant, Lease
from .serializers import PropertySerializer, TenantSerializer, LeaseSerializer
from .serializers.lease_create_serializer import LeaseCreateSerializer
from .grpc_client import send_create_lease_request, GRPCConnectionError, GRPCRequestError

logger = logging.getLogger(__name__) # <-- СОЗДАНИЕ ЛОГГЕРА ДЛЯ МОДУЛЯ

@api_view(['GET', 'POST'])
def property_list_create(request):
# ... (Существующий код) ...
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
# ... (Существующий код) ...
    tenants = Tenant.objects.all()
    serializer = TenantSerializer(tenants, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def lease_list(request):
# ... (Существующий код) ...
    leases = Lease.objects.select_related('property', 'tenant').all()
    serializer = LeaseSerializer(leases, many=True)
    return Response(serializer.data)

# --- ЭНДПОИНТ ДЛЯ СОЗДАНИЯ АРЕНДЫ ЧЕРЕЗ gRPC ---
@api_view(['POST'])
@permission_classes([AllowAny])
def lease_create_grpc(request):
    """
    Принимает HTTP POST запрос, валидирует его и передает 
    данные в сервис FastAPI через gRPC.
    """
    serializer = LeaseCreateSerializer(data=request.data)

    if serializer.is_valid():
        validated_data = serializer.validated_data
        
        # ЛОГ ДЛЯ ОТЛАДКИ
        logger.info(f"DRF VALIDATED DATA: {validated_data}")
        
        # Разделяем данные для удобства передачи в gRPC-клиент
        property_data = validated_data.pop('property')
        tenant_data = validated_data.pop('tenant')
        lease_details = validated_data # Оставшиеся поля (start_date, rent, etc.)
        
        try:
            # 1. Отправляем gRPC-запрос
            response_pb = send_create_lease_request(
                property_data=property_data, 
                tenant_data=tenant_data, 
                lease_details=lease_details
            )

            # 2. Обрабатываем gRPC-ответ
            if response_pb.success:
                # Успех: Формируем чистый JSON-ответ из gRPC-модели Lease
                response_data = {
                    "status": "success",
                    "message": response_pb.message,
                    "lease_id": response_pb.lease.id,
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

        except GRPCConnectionError as e:
            # Ошибка соединения (FastAPI недоступен)
            return Response({
                "status": "error",
                "error": "Service Unavailable",
                "details": str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        except GRPCRequestError as e:
            # Ошибка RPC (например, таймаут, ошибка на сервере FastAPI)
            return Response({
                "status": "error",
                "error": "Internal gRPC Error",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            # Любая непредвиденная ошибка
            return Response({
                "status": "error",
                "error": "Unexpected Error",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    # Ошибка валидации DRF
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
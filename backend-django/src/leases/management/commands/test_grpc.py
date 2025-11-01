import grpc 
from django.core.management.base import BaseCommand
from leases.grpc_client import create_lease

class Command(BaseCommand):
    help = 'Тестирование gRPC-соединения с FastAPI'

    def handle(self, *args, **options):
        property_data = {
            "address": "ул. Ленина, 15",
            "city": "Москва",
            "country": "Россия"
        }
        
        tenant_data = {
            "first_name": "Иван",
            "last_name": "Иванов",
            "email": "ivan@example.com"
        }
        
        lease_data = {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "monthly_rent": 50000.0,
            "payment_day": 1
        }
        
        try:
            response = create_lease(property_data, tenant_data, lease_data)
            self.stdout.write(self.style.SUCCESS(f"Успешно: {response.success}"))
            self.stdout.write(self.style.SUCCESS(f"Сообщение: {response.message}"))
            # self.stdout.write(self.style.SUCCESS(f"ID договора: {response.lease.id}"))
        except grpc.RpcError as e:
            self.stdout.write(self.style.ERROR(f"gRPC ошибка: {e.code()} - {e.details()}"))
import json
import os
from kafka import KafkaProducer
from datetime import datetime
import hashlib

# Инициализация Kafka producer
producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092").split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def send_tenant_event(event_type, tenant):
    """
    Отправка события арендатора.
    Использует tenant.id как django_id.
    """
    event = {
        "event_type": event_type,
        "django_id": tenant.id,
        "fastapi_id": getattr(tenant, "fastapi_id", None),
        "timestamp": datetime.utcnow().isoformat(),
        "details": {
            "first_name": tenant.first_name,
            "last_name": tenant.last_name,
            "email": tenant.email,
            "phone": tenant.phone,
        }
    }
    producer.send("tenant_events", event)
    producer.flush()
    print(f"✅ Tenant Event sent: {event_type} for {tenant.id}")

def _stable_payment_id(event_type: str, payment_data: dict) -> int:
    """
    Детерминированный BIGINT-идентификатор события на основе ключевых полей.
    Нужен как надёжный django_id, если его явно не передали.
    Это позволяет избежать дублей на уровне БД (уникальный индекс).
    """
    # Собираем строку-ключ: тип события + ключевые поля платежа
    key_parts = [
        event_type,
        str(payment_data.get("tenant_id")),
        str(payment_data.get("lease_id")),
        str(payment_data.get("amount")),
        str(payment_data.get("currency")),
        str(payment_data.get("paid_at")),
    ]
    key_str = "|".join(key_parts)

    # Берём SHA-256, превращаем первые 8 байт в BIGINT (0..2^64-1)
    digest = hashlib.sha256(key_str.encode("utf-8")).digest()
    bigint = int.from_bytes(digest[:8], byteorder="big", signed=True)
    return bigint

def send_payment_event(
    event_type: str,
    payment_data: dict,
    django_id: int | None = None,
    fastapi_id: int | None = None
):
    """
    Отправка события платежа.
    - Если django_id не передан, вычисляется стабильный детерминированный идентификатор на основе данных платежа.
    - Это обеспечивает идемпотентность: одинаковые события не дублируются в таблице payments.
    """
    effective_id = django_id if django_id is not None else _stable_payment_id(event_type, payment_data)

    event = {
        "event_type": event_type,
        "django_id": effective_id,  # всегда BIGINT
        "fastapi_id": fastapi_id,
        "timestamp": datetime.utcnow().isoformat(),
        "details": payment_data
    }
    producer.send("payment_events", event)
    producer.flush()
    print(f"✅ Payment Event sent: {event_type} for {effective_id}")

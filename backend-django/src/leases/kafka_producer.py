# leases/kafka_producer.py
import json
import os
from kafka import KafkaProducer
from datetime import datetime

producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092").split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def send_tenant_event(event_type, tenant):
    event = {
        "event_type": event_type,
        "django_id": tenant.id,
        "fastapi_id": getattr(tenant, "fastapi_id", None),
        "timestamp": datetime.now().isoformat(),
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
    
def send_payment_event(event_type: str, payment_data: dict, django_id: int | None = None, fastapi_id: int | None = None):
    event = {
        "event_type": event_type,
        "django_id": django_id,
        "fastapi_id": fastapi_id,
        "timestamp": datetime.utcnow().isoformat(),
        "details": payment_data
    }
    producer.send("payment_events", event)
    producer.flush()
    print(f"✅ Payment Event sent: {event_type} for {django_id or payment_data.get('lease_id')}")
    
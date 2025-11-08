# kafka_consumer.py
import json
import logging
import os
from kafka import KafkaConsumer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

tenant_events_log = []  # глобальный список

def start_tenant_consumer():
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka:29092")
    kafka_topic = "tenant_events"

    consumer = KafkaConsumer(
        kafka_topic,
        bootstrap_servers=[kafka_broker],
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="fastapi-tenant-processor",
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )

    logger.info(f"FastAPI TenantConsumer listening on {kafka_topic}...")

    for message in consumer:
        data = message.value
        tenant_events_log.append(data)   # сохраняем событие
        logger.info(f"Tenant Event: {data}")
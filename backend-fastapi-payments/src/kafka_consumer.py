import json
import logging
import os
from kafka import KafkaConsumer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

payment_events_log = []

def start_payment_consumer():
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka:29092")
    kafka_topic = "payment_events"

    consumer = KafkaConsumer(
        kafka_topic,
        bootstrap_servers=[kafka_broker],
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="fastapi-payment-processor",
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )

    logger.info(f"PaymentConsumer listening on {kafka_topic}...")

    for message in consumer:
        data = message.value
        payment_events_log.append(data)
        logger.info(f"Payment Event: {data}")
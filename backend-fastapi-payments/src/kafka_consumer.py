# backend-fastapi-payments/src/kafka_consumer.py
import json
import logging
import os
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import Json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Храним события в памяти (для REST-эндпоинта /payment-events)
payment_events_log = []

# Подключение к БД
_db_conn = None

def get_conn():
    """
    Возвращает подключение к Postgres.
    Используем одно соединение на процесс.
    """
    global _db_conn
    if _db_conn is None:
        _db_conn = psycopg2.connect(
            dbname="rentflow",
            user="rentuser",
            password="rentpass",
            host="postgres"
        )
        _db_conn.autocommit = True
    return _db_conn


def start_payment_consumer():
    """
    Запускает Kafka consumer, слушает топик payment_events,
    сохраняет события в память и в таблицу payments.
    """
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

        # Сохраняем в БД
        conn = get_conn()
        cur = conn.cursor()
        details = data.get("details", {}) or {}
        try:
            cur.execute(
                """
                INSERT INTO payments (django_id, event_type, ts, tenant_id, lease_id, amount, currency, payload)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (django_id, event_type) WHERE django_id IS NOT NULL DO NOTHING
                """,
                (
                    data.get("django_id"),
                    data.get("event_type"),
                    data.get("timestamp"),
                    details.get("tenant_id"),
                    details.get("lease_id"),
                    details.get("amount"),
                    details.get("currency"),
                    Json(data)
                )
            )
        except Exception as e:
            logger.exception("DB write failed: %s", e)
        finally:
            cur.close()

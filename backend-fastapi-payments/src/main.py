from fastapi import FastAPI, Query, Response
import threading
from kafka_consumer import start_payment_consumer, payment_events_log, get_conn
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Payments Service")

# Метрики
events_counter = Counter("payment_events_total", "Total payment events processed", ["event_type"])
db_errors_counter = Counter("payment_db_errors_total", "Total DB write errors")
processing_time = Histogram("payment_event_processing_seconds", "Time spent processing payment events")

@app.on_event("startup")
def startup_event():
    threading.Thread(target=start_payment_consumer, daemon=True).start()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "payments"}

@app.get("/payment-events")
def get_payment_events(limit: int = 20, event_type: str | None = None):
    if event_type:
        filtered = [e for e in payment_events_log if e.get("event_type") == event_type]
        return filtered[-limit:]
    return payment_events_log[-limit:]

@app.get("/stats")
def payment_stats(
    hours: int = Query(24, ge=1, le=24*30),
    top_tenants: int = Query(10, ge=0, le=100)
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT currency, SUM(amount)::float, COUNT(*)
        FROM payments
        WHERE event_type='PaymentReceived'
          AND ts >= now() - interval '%s hours'
        GROUP BY currency;
        """,
        (hours,)
    )
    totals = [{"currency": c, "total": t, "count": cnt} for c, t, cnt in cur.fetchall()]

    cur.execute(
        """
        SELECT COUNT(*) FROM payments
        WHERE event_type='PaymentDelayed'
          AND ts >= now() - interval '%s hours';
        """,
        (hours,)
    )
    delayed_count = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*) FROM payments
        WHERE event_type='PaymentRefunded'
          AND ts >= now() - interval '%s hours';
        """,
        (hours,)
    )
    refunded_count = cur.fetchone()[0]

    top_by_tenant = []
    if top_tenants > 0:
        cur.execute(
            """
            SELECT tenant_id, SUM(amount)::float AS total
            FROM payments
            WHERE event_type='PaymentReceived'
              AND ts >= now() - interval '%s hours'
            GROUP BY tenant_id
            ORDER BY total DESC
            LIMIT %s;
            """,
            (hours, top_tenants)
        )
        top_by_tenant = [{"tenant_id": tid, "sum": total} for tid, total in cur.fetchall()]

    cur.close()

    return {
        "window_hours": hours,
        "totals": totals,
        "delayed_count": delayed_count,
        "refunded_count": refunded_count,
        "top_tenants": top_by_tenant
    }

@app.get("/metrics")
def metrics():
    """
    Эндпоинт для Prometheus.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

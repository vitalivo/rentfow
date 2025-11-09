from fastapi import FastAPI
import threading
from kafka_consumer import start_payment_consumer, payment_events_log

app = FastAPI(title="Payments Service")

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
from fastapi import FastAPI
import threading
from kafka_consumer import start_tenant_consumer, tenant_events_log


app = FastAPI(title="Tenants Service")

@app.on_event("startup")
def startup_event():
    threading.Thread(target=start_tenant_consumer, daemon=True).start()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "tenants"}

@app.get("/tenant-events")
def get_tenant_events(limit: int = 10, event_type: str | None = None):
    if event_type:
        filtered = [e for e in tenant_events_log if e.get("event_type") == event_type]
        return filtered[-limit:]
    return tenant_events_log[-limit:]



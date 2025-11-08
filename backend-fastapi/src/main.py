import sys
import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, APIRouter, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from kafka import KafkaProducer
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from jose import JWTError, jwt

# === Пути к протоколам ===
PROTO_DIR = "/rentflow_protos"
if PROTO_DIR not in sys.path:
    sys.path.append(PROTO_DIR)

# === Конфигурация ===
KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insecure-dev-key-change-in-prod")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# === Kafka ===
producer: KafkaProducer = None

# === SQLAlchemy ===
engine = create_engine(POSTGRES_URL.replace("+asyncpg", ""))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# === JWT ===
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# === Kafka lifecycle ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    logging.info(f"Connecting to Kafka at: {KAFKA_SERVER}")
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVER.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logging.info("Kafka Producer initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Kafka Producer: {e}")
    yield
    if producer:
        producer.close()
        logging.info("Kafka Producer closed.")

# === FastAPI app ===
app = FastAPI(
    title="RentFlow Tracking Service",
    version="1.0.0",
    # lifespan=lifespan
)

# === Public routes ===
router_events = APIRouter()

@router_events.get("/health")
def health_check():
    kafka_status = "connected" if producer and producer.bootstrap_connected() else "disconnected"
    return JSONResponse(content={"status": "ok", "kafka_status": kafka_status}, status_code=200)

@router_events.get("/grpc-test")
async def grpc_test_route():
    return {"message": "GRPC Test route accessed successfully."}

@router_events.post("/events/track/{topic}")
async def track_event(topic: str, payload: dict):
    if not producer:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kafka Producer not initialized.")
    try:
        future = producer.send(topic, value=payload)
        future.get(timeout=10)
        logging.info(f"Event sent to topic '{topic}' with payload: {payload}")
        return {"status": "success", "topic": topic}
    except Exception as e:
        logging.error(f"Failed to send message to Kafka: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send event: {e}")

app.include_router(router_events)

# === Protected routes ===
router_protected = APIRouter(prefix="/api", tags=["Protected"])

@router_protected.get("/protected/status")
def protected_status(current_user_id: int = Depends(get_current_user)):
    return JSONResponse(content={
        "status": "ok",
        "message": "Access granted",
        "user_id": current_user_id
    }, status_code=status.HTTP_200_OK)
    
@app.get("/__debug__")
def debug():
    return {"status": "main.py active"}   

app.include_router(router_protected)
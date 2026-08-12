from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_app_schema
from app.routers import alerts, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_app_schema()
    yield


app = FastAPI(title="AML Alert Triage API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts.router)
app.include_router(metrics.router)


@app.get("/health")
def health():
    return {"status": "ok"}

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.init_db import init_db
from app.routers import analysis, auth
from app.services.notion_service import check_notion_connection, is_notion_configured


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PumpShield AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analysis.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "pumpshield-ai",
        "notion_configured": is_notion_configured(),
    }


@app.get("/health/notion")
async def health_notion():
    notion = await check_notion_connection()
    return notion

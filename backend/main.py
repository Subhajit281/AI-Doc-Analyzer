from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded before importing application services
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.documents import router as documents_router
from app.api.query import router as query_router
from app.api.auth import router as auth_router
from app.api.payments import router as payments_router
from app.core.database import db_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database connection on startup
    await db_manager.initialize()
    yield

app = FastAPI(
    title="Document AI Analyzer",
    description="Document Analysis & Intelligent Query API",
    version="1.1.0",
    lifespan=lifespan,
)

# ============================================================
# CORS
# ============================================================

import os

# Base development origins
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Additional production origins from environment (comma-separated)
extra_origins = os.getenv("ALLOWED_ORIGINS", "")
if extra_origins:
    allowed_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|https://.*\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Routers
# ============================================================

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

app.include_router(
    payments_router,
    prefix="/payments",
    tags=["Payments"],
)

app.include_router(
    documents_router,
    prefix="/documents",
    tags=["Documents"],
)

app.include_router(
    query_router,
    tags=["Query"],
)

# ============================================================
# Root
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Document AI Analyzer API",
        "status": "running",
    }
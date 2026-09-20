from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded before importing application services
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.api.documents import router as documents_router
from app.api.query import router as query_router
from app.api.auth import router as auth_router
from app.api.payments import router as payments_router
from app.core.database import db_manager
from app.services.auth_service import JWT_SECRET

IS_PRODUCTION = os.getenv("APP_ENV", "development").strip().lower() == "production"

@asynccontextmanager
async def lifespan(app: FastAPI):
    if IS_PRODUCTION and not JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be configured in production.")
    await db_manager.initialize()
    yield

app = FastAPI(
    title="Document AI Analyzer",
    description="Document Analysis & Intelligent Query API",
    version="1.1.0",
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# ============================================================
# CORS
# ============================================================

development_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Additional production origins from environment (comma-separated)
configured_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in configured_origins.split(",") if o.strip()]
if not IS_PRODUCTION:
    allowed_origins.extend(development_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response

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
    payments_router,
    prefix="/api",
    tags=["Payments API"],
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


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}

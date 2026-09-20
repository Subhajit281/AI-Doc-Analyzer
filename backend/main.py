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
from app.services.auth_service import get_jwt_secret
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

IS_PRODUCTION = os.getenv("APP_ENV", "development").strip().lower() == "production"

@asynccontextmanager
async def lifespan(app: FastAPI):
    secret = get_jwt_secret()
    if IS_PRODUCTION and not secret:
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
# Global Exception Handlers
# ============================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = err.get("loc", ["field"])[-1]
        errors.append(f"{field}: {err.get('msg', 'Invalid value')}")
    return JSONResponse(
        status_code=422,
        content={"detail": ", ".join(errors) if errors else "Invalid request data."},
    )

# ============================================================
# CORS
# ============================================================

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

configured_origins = os.getenv("ALLOWED_ORIGINS", "")
if configured_origins:
    allowed_origins.extend([o.strip() for o in configured_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|https://.*\.netlify\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith(("/api", "/auth", "/documents", "/payments")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.query import router as query_router


app = FastAPI(
    title="Document AI Analyzer",
    description="Agentic RAG Document Analysis API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Routers
# ============================================================

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
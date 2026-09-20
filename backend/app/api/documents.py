import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request

from app.services.document_service import (
    process_document,
    delete_document,
)
from app.api.auth import get_current_user_required
from app.core.rate_limit import rate_limiter


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user_required),
    request: Request = None,
):

    # ============================================================
    # Validate upload
    # ============================================================

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided",
        )

    # ============================================================
    # Process document
    # ============================================================

    client_key = "unknown"
    if request:
        client_key = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or request.headers.get("cf-connecting-ip", "").strip()
            or (request.client.host if request.client else "unknown")
        )
    rate_limiter.check(f"upload:{user['id']}:{client_key}", limit=20, window_seconds=3600)

    try:
        result = await process_document(file, user_id=user["id"])
        return result

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )
    except Exception:
        logger.exception("Document processing failed")
        raise HTTPException(
            status_code=500,
            detail="Document processing failed. Please try another supported file.",
        )


@router.get("")
async def list_documents(user: dict = Depends(get_current_user_required)):
    """
    List all active, non-expired documents belonging to the authenticated user.
    """
    from app.core.database import db_manager
    docs = await db_manager.get_user_documents(user["id"])
    return {
        "documents": docs,
        "count": len(docs),
    }


@router.delete("/{document_id}")
async def remove_document(
    document_id: str,
    user: dict = Depends(get_current_user_required),
):
    if not document_id or not document_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Document ID cannot be empty."
        )

    try:
        return await delete_document(document_id.strip(), user_id=user["id"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception:
        logger.exception("Document deletion failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete the document. Please try again."
        )

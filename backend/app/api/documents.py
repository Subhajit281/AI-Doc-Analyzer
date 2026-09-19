from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import traceback

from app.services.document_service import (
    process_document,
    delete_document,
)
from app.api.auth import get_current_user_required


router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user_required),
):

    # ============================================================
    # Validate upload
    # ============================================================

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided"
        )

    # ============================================================
    # Process document
    # ============================================================

    try:

        print("\n" + "=" * 80)
        print("DOCUMENT UPLOAD STARTED")
        print("=" * 80)
        print("Filename:", file.filename)
        print("Content type:", file.content_type)
        print("=" * 80)

        result = await process_document(file, user_id=user["id"])

        print("\n" + "=" * 80)
        print("DOCUMENT PROCESSING SUCCESS")
        print("=" * 80)

        return result

    # ============================================================
    # Validation / expected processing error
    # ============================================================

    except ValueError as exc:

        print("\n" + "=" * 80)
        print("DOCUMENT VALIDATION ERROR")
        print("=" * 80)
        print("Error:", repr(exc))
        traceback.print_exc()
        print("=" * 80)

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    # ============================================================
    # Unexpected error
    # ============================================================

    except Exception as exc:

        print("\n" + "=" * 80)
        print("DOCUMENT PROCESSING FAILED")
        print("=" * 80)

        print("Exception type:", type(exc).__name__)
        print("Exception:", repr(exc))

        print("\nFULL TRACEBACK:")
        traceback.print_exc()

        print("=" * 80)

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(exc)}"
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
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(exc)}"
        )
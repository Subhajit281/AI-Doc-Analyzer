from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
)
from pydantic import BaseModel
from app.services.query_service import query_service
from app.services.auth_service import auth_service, PLAN_LIMITS
from app.api.auth import get_current_user_required
from app.core.database import db_manager

router = APIRouter()

# ============================================================
# Request Schema
# ============================================================

class QueryRequest(BaseModel):
    query: str
    conversation_id: str


# ============================================================
# Query Endpoint
# ============================================================

@router.post(
    "/documents/{document_id}/query"
)
async def query_document(
    document_id: str,
    request: QueryRequest,
    user: dict = Depends(get_current_user_required),
):
    """
    Ask a question about a previously uploaded document.
    Strictly requires authentication (no guest mode).
    Enforces a 24-hour renewable daily quota (10 free queries / 24h).
    """

    # --------------------------------------------------------
    # Validate inputs
    # --------------------------------------------------------

    if not document_id or not document_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Document ID cannot be empty.",
        )

    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )

    if not request.conversation_id or not request.conversation_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Conversation ID cannot be empty.",
        )

    # --------------------------------------------------------
    # Verify User Quota & Active Subscription (24h Rollover)
    # --------------------------------------------------------

    refreshed_user = await db_manager.check_and_refresh_quota(user["id"])
    if refreshed_user:
        user_profile = auth_service.serialize_user(refreshed_user)
    else:
        user_profile = user

    plan = user_profile.get("plan", "free")
    is_pro = user_profile.get("is_pro", False)
    limit = PLAN_LIMITS.get(plan, 10)
    used_today = user_profile.get("query_count_today", 0)

    if used_today >= limit:
        raise HTTPException(
            status_code=402,
            detail="QUOTA_EXCEEDED",
        )

    # --------------------------------------------------------
    # Verify Document Ownership & 7-Day Expiration in DB
    # --------------------------------------------------------

    doc = await db_manager.get_document(document_id=document_id.strip(), user_id=user["id"])
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found or has expired after 7 days.",
        )

    # --------------------------------------------------------
    # Execute RAG Query (Tiered: Fast 8B for Free, GPT-OSS 120B for Pro)
    # --------------------------------------------------------

    try:
        result = query_service.query(
            document_id=document_id.strip(),
            query=request.query.strip(),
            conversation_id=request.conversation_id.strip(),
            is_pro=is_pro,
            manifest=doc.get("manifest"),
        )

        # ----------------------------------------------------
        # Increment quota & persist history
        # ----------------------------------------------------
        updated_doc = await db_manager.increment_user_query_count(user["id"])
        await db_manager.log_user_query(user["id"], document_id.strip(), request.query.strip())

        if updated_doc:
            result["user_quota"] = auth_service.serialize_user(updated_doc)
        else:
            result["user_quota"] = user_profile

        return result

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        print(
            f"Query error for document {document_id}: {repr(exc)}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process the document query.",
        )
from fastapi import (
    APIRouter,
    HTTPException,
)

from pydantic import BaseModel

from app.services.query_service import (
    query_service,
)


router = APIRouter()


# ============================================================
# Request Schema
# ============================================================

class QueryRequest(BaseModel):
    query: str


# ============================================================
# Query Endpoint
# ============================================================

@router.post(
    "/documents/{document_id}/query"
)
async def query_document(
    document_id: str,
    request: QueryRequest,
):
    """
    Ask a question about a previously uploaded document.

    The document must already have been processed and
    stored in the local RAG system.
    """

    # --------------------------------------------------------
    # Validate document ID
    # --------------------------------------------------------

    if not document_id or not document_id.strip():

        raise HTTPException(
            status_code=400,
            detail="Document ID cannot be empty.",
        )

    # --------------------------------------------------------
    # Validate query
    # --------------------------------------------------------

    if not request.query or not request.query.strip():

        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )

    try:

        result = query_service.query(
            document_id=document_id.strip(),
            query=request.query.strip(),
        )

        return result

    # --------------------------------------------------------
    # Document not found
    # --------------------------------------------------------

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    # --------------------------------------------------------
    # Invalid request
    # --------------------------------------------------------

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # --------------------------------------------------------
    # Unexpected agent/RAG error
    # --------------------------------------------------------

    except Exception as exc:

        print(
            f"Query error for document "
            f"{document_id}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to process the document query."
            ),
        )
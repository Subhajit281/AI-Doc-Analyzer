from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.document_service import process_document


router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided"
        )

    try:

        result = await process_document(file)

        return result

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(exc)}"
        )
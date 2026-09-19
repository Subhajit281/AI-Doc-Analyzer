from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.payment_service import payment_service
from app.api.auth import get_current_user_required

router = APIRouter()

class CreateOrderRequest(BaseModel):
    plan: str
    currency: str = "INR"

class VerifyPaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str = ""

@router.get("/plans")
async def get_plans():
    return payment_service.get_plans()

@router.post("/create-order")
async def create_order(
    req: CreateOrderRequest,
    user: dict = Depends(get_current_user_required),
):
    try:
        return await payment_service.create_order(
            user_id=user["id"],
            plan_id=req.plan,
            currency=req.currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(exc)}")

@router.post("/verify")
async def verify_payment(
    req: VerifyPaymentRequest,
    user: dict = Depends(get_current_user_required),
):
    try:
        return await payment_service.verify_payment(
            order_id=req.order_id,
            payment_id=req.payment_id,
            signature=req.signature,
            user_id=user["id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(exc)}")


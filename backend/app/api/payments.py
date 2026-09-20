from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.payment_service import payment_service
from app.api.auth import get_current_user_required

router = APIRouter()


class CreateOrderRequest(BaseModel):
    amount: int | None = None          # in paise (e.g., 2900 for ₹29)
    plan: str | None = None            # 'day', 'month', 'year'
    currency: str = "INR"
    receipt: str | None = None


class VerifyPaymentRequest(BaseModel):
    # Support both custom and standard Razorpay checkout response field names
    order_id: str | None = None
    payment_id: str | None = None
    signature: str | None = None
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    razorpay_signature: str | None = None


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
            amount_paise=req.amount,
            currency=req.currency,
            receipt=req.receipt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(exc)}")


@router.post("/verify")
@router.post("/verify-payment")
async def verify_payment(
    req: VerifyPaymentRequest,
    user: dict = Depends(get_current_user_required),
):
    order_id = req.order_id or req.razorpay_order_id
    payment_id = req.payment_id or req.razorpay_payment_id
    signature = req.signature or req.razorpay_signature

    if not order_id or not payment_id or not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: order_id, payment_id, and signature are required.",
        )

    try:
        return await payment_service.verify_payment(
            order_id=order_id,
            payment_id=payment_id,
            signature=signature,
            user_id=user["id"],
        )
    except ValueError as exc:
        # Signature mismatch or order not found -> 400
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(exc)}")

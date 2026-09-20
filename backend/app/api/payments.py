from fastapi import APIRouter, HTTPException, Depends
from typing import Literal

from pydantic import BaseModel, ConfigDict
from app.services.payment_service import payment_service
from app.api.auth import get_current_user_required

router = APIRouter()


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    plan: Literal["day", "month", "year"] | None = None
    amount: int | float | None = None
    currency: Literal["INR", "USD"] = "INR"
    receipt: str | None = None


class VerifyPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
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


@router.get("/status/{order_id}")
async def get_order_status(
    order_id: str,
    user: dict = Depends(get_current_user_required),
):
    try:
        return await payment_service.get_payment_status(order_id=order_id.strip(), user_id=user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to retrieve payment status.")


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
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to create a payment order right now.")


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
    except HTTPException:
        raise
    except ValueError as exc:
        # Signature mismatch or order not found -> 400
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to verify the payment right now.")


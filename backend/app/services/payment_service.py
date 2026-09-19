import os
import hmac
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from app.core.database import db_manager, ensure_utc

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_MERCHANT_UPI = os.getenv("RAZORPAY_MERCHANT_UPI", "docai@razorpay").strip()

PLANS = {
    "day": {
        "id": "day",
        "name": "Day Pass",
        "price_inr": 29,
        "price_usd": 0.49,
        "duration_days": 1,
        "query_limit": 100,
        "features": [
            "100 Inquiries / 24 Hours",
            "OpenAI GPT-OSS 120B Reasoning Model",
            "Multi-format Document Analysis (up to 10 MB)",
            "Instant Verification & Cited Evidence",
        ],
    },
    "month": {
        "id": "month",
        "name": "Monthly Pro",
        "price_inr": 199,
        "price_usd": 2.49,
        "duration_days": 30,
        "query_limit": 500,
        "popular": True,
        "features": [
            "500 Inquiries / Month (100 / day)",
            "OpenAI GPT-OSS 120B Flagship Model",
            "Complex Table & Formula Extraction",
            "Priority Multi-page Analysis Queue",
            "Full Purchase History & Receipts",
        ],
    },
    "year": {
        "id": "year",
        "name": "Annual Pro",
        "price_inr": 1499,
        "price_usd": 17.99,
        "duration_days": 365,
        "query_limit": 2500,
        "features": [
            "2,500 Inquiries / Year (200 / day)",
            "OpenAI GPT-OSS 120B Deep Context Inference",
            "Continuous Priority Ingestion & Analysis",
            "All Monthly Pro Capabilities Included",
            "Maximum Value & 40% Annual Savings",
        ],
    },
}

class PaymentService:
    def __init__(self):
        self._client = None
        if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
            try:
                import razorpay
                self._client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
            except Exception as e:
                print(f"[PAYMENT] Razorpay client initialization error: {e}")

    def get_plans(self) -> dict:
        return PLANS

    async def create_order(self, user_id: str, plan_id: str, currency: str = "INR") -> dict:
        if plan_id not in PLANS:
            raise ValueError(f"Invalid plan: '{plan_id}'. Choose from: day, month, year.")

        plan = PLANS[plan_id]
        currency = currency.upper()

        if currency == "USD":
            amount_display = plan["price_usd"]
            amount_cents = int(round(amount_display * 100))
            order_currency = "USD"
            inr_equivalent = plan["price_inr"]
        else:
            amount_display = plan["price_inr"]
            amount_cents = int(round(amount_display * 100))  # in paise
            order_currency = "INR"
            inr_equivalent = plan["price_inr"]

        order_id = ""
        if self._client:
            try:
                order_data = {
                    "amount": amount_cents,
                    "currency": order_currency,
                    "receipt": f"rcpt_{user_id[:8]}_{int(datetime.now().timestamp())}",
                    "payment_capture": 1,
                    "notes": {
                        "user_id": user_id,
                        "plan": plan_id,
                    },
                }
                rp_order = self._client.order.create(data=order_data)
                order_id = rp_order["id"]
            except Exception as e:
                print(f"[PAYMENT] Razorpay API order creation warning: {e}. Falling back to standard order ID.")
                order_id = f"order_{uuid.uuid4().hex[:14]}"
        else:
            order_id = f"order_{uuid.uuid4().hex[:14]}"

        # Generate universal UPI intent string for dynamic QR rendering
        upi_string = (
            f"upi://pay?pa={RAZORPAY_MERCHANT_UPI}&pn=DocAI%20Analyzer"
            f"&am={inr_equivalent:.2f}&cu=INR&tr={order_id}"
        )

        payment_record = {
            "user_id": user_id,
            "order_id": order_id,
            "plan": plan_id,
            "amount": amount_display,
            "currency": order_currency,
            "amount_inr": inr_equivalent,
            "status": "created",
            "upi_intent": upi_string,
        }
        await db_manager.create_payment_order(payment_record)

        return {
            "order_id": order_id,
            "plan": plan,
            "amount": amount_display,
            "currency": order_currency,
            "amount_inr": inr_equivalent,
            "key_id": RAZORPAY_KEY_ID or "rzp_test_public_key",
            "upi_qr_data": upi_string,
        }

    async def verify_payment(self, order_id: str, payment_id: str, signature: str, user_id: str) -> dict:
        payment = await db_manager.get_payment_by_order_id(order_id)
        if not payment:
            raise ValueError("Payment order not found.")

        # Signature verification if secret is provided
        if RAZORPAY_KEY_SECRET:
            try:
                msg = f"{order_id}|{payment_id}".encode("utf-8")
                expected_signature = hmac.new(
                    RAZORPAY_KEY_SECRET.encode("utf-8"),
                    msg,
                    hashlib.sha256,
                ).hexdigest()

                if not hmac.compare_digest(expected_signature, signature):
                    raise ValueError("Payment verification signature mismatch.")
            except Exception as exc:
                if "signature mismatch" in str(exc):
                    raise
                print(f"[PAYMENT] Signature check error: {exc}")

        # Update payment record
        updated_payment = await db_manager.mark_payment_paid(
            order_id=order_id,
            payment_id=payment_id,
            signature=signature,
        )

        # Extend user subscription
        plan_id = payment.get("plan", "month")
        plan = PLANS.get(plan_id, PLANS["month"])
        duration = timedelta(days=plan["duration_days"])

        now_utc = datetime.now(timezone.utc)
        user = await db_manager.get_user_by_id(user_id)
        current_expiry = user.get("plan_expires_at") if user else None

        if current_expiry:
            cur_dt = ensure_utc(current_expiry)
            if cur_dt and cur_dt > now_utc:
                new_expiry = cur_dt + duration
            else:
                new_expiry = now_utc + duration
        else:
            new_expiry = now_utc + duration

        await db_manager.update_user(user_id, {
            "plan": plan_id,
            "plan_expires_at": new_expiry.isoformat(),
        })

        return {
            "status": "success",
            "order_id": order_id,
            "payment_id": payment_id,
            "plan": plan_id,
            "plan_expires_at": new_expiry.isoformat(),
        }

payment_service = PaymentService()


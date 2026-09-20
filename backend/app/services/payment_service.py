import os
import hmac
import hashlib
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import dotenv_values, load_dotenv
from app.core.database import db_manager, ensure_utc

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)
load_dotenv()

# Default fallback test credentials in case .env is missing/corrupted
DEFAULT_TEST_KEY_ID = "rzp_test_TeFbpgyeysB2BK"
DEFAULT_TEST_KEY_SECRET = "OGTYYGxZ6AkS1IwNoxnkDkUB"


def get_razorpay_key_id() -> str:
    """Dynamically reads RAZORPAY_KEY_ID from .env or os.environ."""
    if _env_path.exists():
        vals = dotenv_values(_env_path)
        val = vals.get("RAZORPAY_KEY_ID")
        if val and val.strip():
            return val.strip()
    return os.getenv("RAZORPAY_KEY_ID", "").strip() or DEFAULT_TEST_KEY_ID


def get_razorpay_key_secret() -> str:
    """Dynamically reads RAZORPAY_KEY_SECRET (or common typos) from .env or os.environ."""
    if _env_path.exists():
        vals = dotenv_values(_env_path)
        for k in ("RAZORPAY_KEY_SECRET", "RAZORPAY_KEY_SECRE", "RAZORPAY_SECRET"):
            val = vals.get(k)
            if val and val.strip():
                return val.strip()
    for k in ("RAZORPAY_KEY_SECRET", "RAZORPAY_KEY_SECRE", "RAZORPAY_SECRET"):
        val = os.getenv(k, "").strip()
        if val:
            return val
    return DEFAULT_TEST_KEY_SECRET


def get_razorpay_merchant_upi() -> str:
    if _env_path.exists():
        vals = dotenv_values(_env_path)
        val = vals.get("RAZORPAY_MERCHANT_UPI")
        if val and val.strip():
            return val.strip()
    return os.getenv("RAZORPAY_MERCHANT_UPI", "subhajitsarkar281@oksbi").strip()


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
    def get_client(self):
        key_id = get_razorpay_key_id()
        key_secret = get_razorpay_key_secret()
        if key_id and key_secret:
            try:
                import razorpay
                return razorpay.Client(auth=(key_id, key_secret))
            except Exception as e:
                print(f"[PAYMENT] Razorpay client init error: {e}")
        return None

    def get_plans(self) -> dict:
        return PLANS

    async def create_order(
        self,
        user_id: str,
        plan_id: str | None = None,
        amount_paise: int | None = None,
        currency: str = "INR",
        receipt: str | None = None,
    ) -> dict:
        currency = currency.upper()

        # Determine amount and plan
        if amount_paise is not None:
            if amount_paise < 100:
                raise ValueError("Minimum amount is 100 paise (₹1.00).")
            amount_cents = int(amount_paise)
            matched_plan = None
            for p in PLANS.values():
                if int(round(p["price_inr"] * 100)) == amount_cents:
                    matched_plan = p
                    plan_id = p["id"]
                    break
            plan = matched_plan or {
                "id": plan_id or "custom",
                "name": "Pro Subscription",
                "price_inr": amount_cents / 100.0,
                "price_usd": round(amount_cents / 8300.0, 2),
                "duration_days": 30,
            }
            amount_display = amount_cents / 100.0
            inr_equivalent = amount_cents / 100.0
        elif plan_id:
            if plan_id not in PLANS:
                raise ValueError(f"Invalid plan: '{plan_id}'. Choose from: day, month, year.")
            plan = PLANS[plan_id]
            if currency == "USD":
                amount_display = plan["price_usd"]
                amount_cents = int(round(amount_display * 100))
                inr_equivalent = plan["price_inr"]
            else:
                amount_display = plan["price_inr"]
                amount_cents = int(round(amount_display * 100))
                inr_equivalent = plan["price_inr"]
            if amount_cents < 100:
                raise ValueError("Minimum amount is 100 paise (₹1.00).")
        else:
            plan_id = "month"
            plan = PLANS["month"]
            amount_display = plan["price_inr"]
            amount_cents = int(round(amount_display * 100))
            inr_equivalent = plan["price_inr"]

        order_receipt = receipt or f"rcpt_{user_id[:8]}_{int(datetime.now().timestamp())}"

        client = self.get_client()
        if not client:
            raise RuntimeError(
                "Razorpay client initialization failed. Please ensure RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are configured."
            )

        try:
            order_data = {
                "amount": amount_cents,
                "currency": currency,
                "receipt": order_receipt,
                "payment_capture": 1,
                "notes": {
                    "user_id": user_id,
                    "plan": plan_id or "custom",
                },
            }
            rp_order = client.order.create(data=order_data)
            order_id = rp_order["id"]
        except Exception as e:
            raise RuntimeError(f"Razorpay API order creation failed: {e}")

        # Universal UPI string for optional QR display
        merchant_upi = get_razorpay_merchant_upi()
        upi_string = (
            f"upi://pay?pa={merchant_upi}&pn=DocAI%20Analyzer"
            f"&am={inr_equivalent:.2f}&cu=INR&tr={order_id}"
        )

        active_key_id = get_razorpay_key_id()

        payment_record = {
            "user_id": user_id,
            "order_id": order_id,
            "plan": plan_id or "custom",
            "amount": amount_cents,
            "currency": currency,
            "amount_display": amount_display,
            "amount_inr": inr_equivalent,
            "receipt": order_receipt,
            "status": "created",
            "upi_intent": upi_string,
            "key_id": active_key_id,
        }
        await db_manager.create_payment_order(payment_record)

        return {
            "order_id": order_id,
            "amount": amount_cents,
            "currency": currency,
            "receipt": order_receipt,
            "key_id": active_key_id,
            "plan": plan,
            "amount_display": amount_display,
            "amount_inr": inr_equivalent,
            "upi_qr_data": upi_string,
        }

    async def verify_payment(self, order_id: str, payment_id: str, signature: str, user_id: str) -> dict:
        if not order_id or not payment_id or not signature:
            raise ValueError("Missing required payment verification fields: order_id, payment_id, and signature are required.")

        payment = await db_manager.get_payment_by_order_id(order_id)
        if not payment:
            raise ValueError(f"Payment order '{order_id}' not found in database.")

        key_secret = get_razorpay_key_secret()
        if not key_secret:
            raise RuntimeError("RAZORPAY_KEY_SECRET is not configured on the server.")

        # Signature verification: HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET)
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        expected_signature = hmac.new(
            key_secret.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            raise ValueError("Payment verification failed: Signature mismatch.")

        # Update payment record in database
        await db_manager.mark_payment_paid(
            order_id=order_id,
            payment_id=payment_id,
            signature=signature,
        )

        # Extend user subscription
        plan_id = payment.get("plan", "month")
        plan = PLANS.get(plan_id, PLANS.get("month", {}))
        duration_days = plan.get("duration_days", 30)
        duration = timedelta(days=duration_days)

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
            "message": "Payment verified successfully",
            "order_id": order_id,
            "payment_id": payment_id,
            "plan": plan_id,
            "plan_expires_at": new_expiry.isoformat(),
        }


payment_service = PaymentService()

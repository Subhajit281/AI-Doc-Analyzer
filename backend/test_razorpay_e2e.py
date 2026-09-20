import asyncio
import sys
import os
import hmac
import hashlib
from pathlib import Path
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import app
from app.core.database import db_manager
from app.services.auth_service import auth_service
from app.services.payment_service import get_razorpay_key_id, get_razorpay_key_secret


async def run_tests():
    print("=" * 80)
    print("RAZORPAY STANDARD WEB CHECKOUT - END-TO-END VERIFICATION")
    print("=" * 80)

    # 1. Initialize DB
    await db_manager.initialize()
    print("1. Database initialized.")

    # 2. Check Credentials
    key_id = get_razorpay_key_id()
    key_secret = get_razorpay_key_secret()
    print(f"2. Razorpay Credentials Loaded:")
    print(f"   KEY_ID: {key_id[:8]}... (length: {len(key_id)})")
    print(f"   KEY_SECRET: {key_secret[:4]}... (length: {len(key_secret)})")
    assert key_id.startswith(("rzp_test_", "rzp_live_")), "Invalid key id format"
    assert len(key_secret) > 10, "Invalid key secret"

    # 3. Create test user and token
    test_email = f"rzp_user_{int(asyncio.get_event_loop().time())}@test.com"
    user, token = await auth_service.register(test_email, "TestPass123!", "Razorpay Tester")
    print(f"3. Registered test user: {test_email} (ID: {user['id']})")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 4. Test 401 Unauthorized for create-order without auth
        print("4. Testing unauthenticated order creation (expects 401)...")
        res_noauth = await client.post("/api/create-order", json={"amount": 2900, "currency": "INR"})
        assert res_noauth.status_code == 401, f"Expected 401, got {res_noauth.status_code}"
        print("   ✓ Correctly returned 401 Unauthorized.")

        # 5. Test validation: amount < 100 paise (expects 400)
        print("5. Testing minimum amount validation < 100 paise (expects 400)...")
        res_small = await client.post(
            "/api/create-order",
            json={"amount": 50, "currency": "INR"},
            headers=auth_headers,
        )
        assert res_small.status_code == 400, f"Expected 400, got {res_small.status_code}"
        print(f"   ✓ Correctly rejected with 400: {res_small.json()['detail']}")

        # 6. Test successful order creation: POST /api/create-order with amount
        print("6. Testing POST /api/create-order with amount (100 paise)...")
        res_order = await client.post(
            "/api/create-order",
            json={"amount": 100, "currency": "INR", "receipt": "test_receipt_100"},
            headers=auth_headers,
        )
        assert res_order.status_code == 200, f"Expected 200, got {res_order.status_code}: {res_order.text}"
        order_data = res_order.json()
        assert "order_id" in order_data and order_data["order_id"].startswith("order_")
        assert order_data["amount"] == 100
        assert order_data["currency"] == "INR"
        print(f"   ✓ Order created successfully via Razorpay API:")
        print(f"     Order ID: {order_data['order_id']}")
        print(f"     Amount: {order_data['amount']} paise")
        print(f"     Currency: {order_data['currency']}")

        # 7. Test plan-based order creation: POST /payments/create-order
        print("7. Testing POST /payments/create-order with plan='day'...")
        res_plan_order = await client.post(
            "/payments/create-order",
            json={"plan": "day", "currency": "INR"},
            headers=auth_headers,
        )
        assert res_plan_order.status_code == 200, f"Expected 200, got {res_plan_order.status_code}: {res_plan_order.text}"
        plan_order = res_plan_order.json()
        assert plan_order["amount"] == 2900  # ₹29 in paise
        print(f"   ✓ Plan order created: {plan_order['order_id']} ({plan_order['amount']} paise)")

        # 8. Test verify payment - Missing Fields (expects 400)
        print("8. Testing POST /api/verify-payment with missing fields (expects 400)...")
        res_missing = await client.post(
            "/api/verify-payment",
            json={"order_id": order_data["order_id"]},
            headers=auth_headers,
        )
        assert res_missing.status_code == 400, f"Expected 400, got {res_missing.status_code}"
        print(f"   ✓ Correctly rejected missing fields: {res_missing.json()['detail']}")

        # 9. Test verify payment - Invalid Signature / Mismatch (expects 400)
        print("9. Testing POST /api/verify-payment with invalid signature (expects 400)...")
        fake_payment_id = "pay_fake123456"
        bad_signature = "bad_invalid_signature_hex_0000000000"
        res_bad_sig = await client.post(
            "/api/verify-payment",
            json={
                "order_id": order_data["order_id"],
                "payment_id": fake_payment_id,
                "signature": bad_signature,
            },
            headers=auth_headers,
        )
        assert res_bad_sig.status_code == 400, f"Expected 400, got {res_bad_sig.status_code}"
        print(f"   ✓ Correctly rejected signature mismatch: {res_bad_sig.json()['detail']}")

        # Verify payment was NOT marked as paid in DB
        db_payment = await db_manager.get_payment_by_order_id(order_data["order_id"])
        assert db_payment["status"] == "created", f"Payment should NOT be paid, got {db_payment['status']}"
        print("   ✓ Confirmed payment order remains status='created' in DB.")

        # 10. Test verify payment - Valid HMAC-SHA256 Signature (expects 200)
        print("10. Testing POST /api/verify-payment with valid HMAC-SHA256 signature...")
        test_payment_id = "pay_test_78910"
        msg = f"{order_data['order_id']}|{test_payment_id}".encode("utf-8")
        valid_signature = hmac.new(key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        res_valid_sig = await client.post(
            "/api/verify-payment",
            json={
                "order_id": order_data["order_id"],
                "payment_id": test_payment_id,
                "signature": valid_signature,
            },
            headers=auth_headers,
        )
        assert res_valid_sig.status_code == 200, f"Expected 200, got {res_valid_sig.status_code}: {res_valid_sig.text}"
        verify_resp = res_valid_sig.json()
        assert verify_resp["status"] == "success"
        assert verify_resp["payment_id"] == test_payment_id
        print("   ✓ Payment signature verified successfully!")
        print(f"     Status: {verify_resp['status']}")
        print(f"     Order ID: {verify_resp['order_id']}")
        print(f"     Plan Expires: {verify_resp['plan_expires_at']}")

        # Confirm marked as paid in DB
        paid_record = await db_manager.get_payment_by_order_id(order_data["order_id"])
        assert paid_record["status"] == "paid"
        assert paid_record["payment_id"] == test_payment_id
        print("   ✓ Verified database record updated to status='paid' with signature.")

    print("=" * 80)
    print("ALL RAZORPAY INTEGRATION VERIFICATION TESTS PASSED SUCCESSFULLY! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_tests())


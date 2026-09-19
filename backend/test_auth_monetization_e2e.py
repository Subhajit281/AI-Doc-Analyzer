import asyncio
import sys
import os
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend dir to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import db_manager
from app.services.auth_service import auth_service
from app.services.payment_service import payment_service

async def run_monetization_test():
    print("=" * 80)
    print("DOCUMENT AI - AUTH, 10-QUERY QUOTA & RAZORPAY MONETIZATION TEST")
    print("=" * 80)

    # 1. Initialize DB
    await db_manager.initialize()
    print("1. Database Manager initialized successfully.")

    # 2. Test User Registration & Password Hashing
    test_email = f"tester_{int(asyncio.get_event_loop().time())}@example.com"
    test_password = "SecurePassword123"
    print(f"2. Registering new user: {test_email}...")
    user, token = await auth_service.register(test_email, test_password, "Test User")
    print(f"   Registered user ID: {user['id']}")
    print(f"   JWT Token generated (length {len(token)})")
    assert user["query_count"] == 0
    assert user["plan"] == "free"
    assert user["free_queries_remaining"] == 10
    assert not user["is_pro"]

    # 3. Test Authentication (Login)
    print("3. Testing user authentication...")
    logged_user, login_token = await auth_service.authenticate(test_email, test_password)
    assert logged_user["id"] == user["id"]
    print("   Authentication succeeded.")

    # 4. Test 10-Query Quota Simulation
    print("4. Simulating 10 free queries...")
    for i in range(1, 11):
        count = await db_manager.increment_user_query_count(user["id"])
        await db_manager.log_user_query(user["id"], "doc-test-123", f"Query #{i}")
        assert count == i
    print(f"   10 queries executed. Total user queries: {count}")

    # Check that quota is exhausted
    fresh_user = await auth_service.get_user_from_token(token)
    assert fresh_user["query_count"] == 10
    assert fresh_user["free_queries_remaining"] == 0
    assert not fresh_user["is_pro"]
    print("   Quota successfully reached 10/10. Free queries remaining: 0.")

    # 5. Test Pricing Order Creation (INR & USD)
    print("5. Testing order creation for Day Pass & Monthly Pro...")
    inr_order = await payment_service.create_order(user["id"], "day", "INR")
    print(f"   INR Day Pass Order: ID={inr_order['order_id']}, Amount=₹{inr_order['amount_inr']}, UPI QR URI={inr_order['upi_qr_data'][:40]}...")
    assert inr_order["amount"] == 29
    assert inr_order["currency"] == "INR"

    usd_order = await payment_service.create_order(user["id"], "month", "USD")
    print(f"   USD Monthly Pro Order: ID={usd_order['order_id']}, Amount=${usd_order['amount']}, INR Eq=₹{usd_order['amount_inr']}")
    assert usd_order["amount"] == 2.49
    assert usd_order["currency"] == "USD"

    # 6. Test Payment Verification and Upgrade to Pro
    print("6. Verifying payment and upgrading user...")
    verify_res = await payment_service.verify_payment(
        order_id=usd_order["order_id"],
        payment_id="pay_simulated_987654",
        signature="",
        user_id=user["id"],
    )
    assert verify_res["status"] == "success"
    assert verify_res["plan"] == "month"
    print(f"   Payment verified. New plan: {verify_res['plan']}, Expiration: {verify_res['plan_expires_at']}")

    # Check fresh user profile after upgrade
    upgraded_user = await auth_service.get_user_from_token(token)
    assert upgraded_user["is_pro"] is True
    assert upgraded_user["plan"] == "month"
    print(f"   User is now PRO! is_pro={upgraded_user['is_pro']}. Unlimited queries unlocked.")

    # 7. Test Purchase History Timeline
    print("7. Verifying purchase history & timeline records...")
    payments = await db_manager.get_user_payments(user["id"])
    print(f"   Recorded payments found: {len(payments)}")
    assert len(payments) >= 2
    paid_payment = next(p for p in payments if p["order_id"] == usd_order["order_id"])
    assert paid_payment["status"] == "paid"
    print(f"   Purchase timeline verified! Paid order {paid_payment['order_id']} logged with amount ${paid_payment['amount']}.")

    print("=" * 80)
    print("ALL AUTH, QUOTA & MONETIZATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_monetization_test())

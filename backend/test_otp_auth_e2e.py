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

async def run_otp_tests():
    print("=" * 80)
    print("DOCUMENT AI - CRYPTOGRAPHIC OTP AUTHENTICATION TEST")
    print("=" * 80)

    # 1. Initialize DB
    await db_manager.initialize()
    print("1. Database initialized.")

    test_email = f"otp_user_{int(asyncio.get_event_loop().time())}@example.com"
    print(f"2. Requesting OTP for: {test_email}...")

    # Send OTP
    send_res = await auth_service.generate_and_send_otp(test_email, purpose="login")
    assert send_res["success"] is True
    raw_otp = send_res.get("debug_otp")
    assert raw_otp is not None and len(raw_otp) == 6
    print(f"   OTP generated securely (6-digit numeric). Encrypted hash stored.")

    # 3. Test Rate Limiting
    print("3. Testing rate limit (attempting duplicate request immediately)...")
    try:
        await auth_service.generate_and_send_otp(test_email, purpose="login")
        raise AssertionError("Rate limit check failed!")
    except ValueError as e:
        print(f"   Rate limit caught correctly: {e}")

    # 4. Test Invalid OTP Attempt
    print("4. Testing invalid OTP code...")
    try:
        await auth_service.verify_otp_and_authenticate(test_email, "000000", purpose="login")
        raise AssertionError("Invalid OTP check failed!")
    except ValueError as e:
        print(f"   Invalid OTP rejected correctly: {e}")

    # 5. Test Valid OTP Verification & Token Issuance
    print(f"5. Testing valid OTP verification with code {raw_otp}...")
    user, token = await auth_service.verify_otp_and_authenticate(
        email=test_email,
        otp_code=raw_otp,
        purpose="login",
        full_name="OTP Verified User",
    )
    assert user["email"] == test_email
    assert user["full_name"] == "OTP Verified User"
    assert len(token) > 50
    print(f"   Authentication succeeded! User ID={user['id']}, Token Issued.")

    # 6. Verify User Identity via Token
    print("6. Verifying JWT identity token...")
    verified_user = await auth_service.get_user_from_token(token)
    assert verified_user["id"] == user["id"]
    assert verified_user["email"] == test_email
    print(f"   JWT token verified successfully for {verified_user['email']}.")

    # 7. Test OTP Replay Prevention (used OTP is purged)
    print("7. Testing OTP replay protection (re-submitting same code)...")
    try:
        await auth_service.verify_otp_and_authenticate(test_email, raw_otp, purpose="login")
        raise AssertionError("Replay protection failed!")
    except ValueError as e:
        print(f"   Replay blocked correctly: {e}")

    print("=" * 80)
    print("ALL OTP AUTHENTICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_otp_tests())


import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import httpx
import jwt

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import app
from app.core.database import db_manager
from app.services.auth_service import auth_service, get_jwt_secret, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS


async def run_auth_tests():
    print("=" * 80)
    print("AUTHENTICATION & 7-DAY SESSION LIFECYCLE VERIFICATION")
    print("=" * 80)

    await db_manager.initialize()
    print("1. Database initialized.")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # ------------------------------------------------------------------
        # 1. Test Signup & 7-Day Token + Session ID Issuance
        # ------------------------------------------------------------------
        test_email = f"session_test_{int(asyncio.get_event_loop().time())}@test.com"
        password = "SecurePass123"

        print(f"2. Testing POST /auth/signup for {test_email}...")
        signup_res = await client.post(
            "/auth/signup",
            json={
                "email": test_email,
                "password": password,
                "full_name": "Session Tester",
            },
        )
        assert signup_res.status_code == 200, f"Signup failed: {signup_res.text}"
        signup_data = signup_res.json()

        assert "token" in signup_data, "Token missing in signup response"
        assert "session_id" in signup_data, "session_id missing in signup response"
        assert signup_data["expires_in_days"] == 7, f"Expected 7 days expiry, got {signup_data['expires_in_days']}"
        print(f"   ✓ Signup successful! Session ID: {signup_data['session_id']}")

        # Verify decoded JWT payload
        token = signup_data["token"]
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_dt = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        lifetime = exp_dt - iat_dt

        print(f"   ✓ Token IAT: {iat_dt.isoformat()}, EXP: {exp_dt.isoformat()}")
        print(f"   ✓ Exact Token Lifetime: {lifetime.total_seconds() / 86400:.1f} days")
        assert round(lifetime.total_seconds() / 86400) == 7, "Token lifetime is not 7 days!"
        assert payload.get("session_id") == signup_data["session_id"], "Token session_id mismatch"

        # Verify session recorded in DB
        db_session = await db_manager.get_session(signup_data["session_id"])
        assert db_session is not None, "Session record not found in database"
        assert db_session["user_id"] == signup_data["user"]["id"]
        print("   ✓ Active session verified in database.")

        # ------------------------------------------------------------------
        # 2. Test Login & 7-Day Session Issuance
        # ------------------------------------------------------------------
        print("3. Testing POST /auth/login...")
        login_res = await client.post(
            "/auth/login",
            json={"email": test_email, "password": password},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        login_data = login_res.json()
        assert login_data["expires_in_days"] == 7
        assert "session_id" in login_data
        print(f"   ✓ Login successful! New Session ID: {login_data['session_id']}")

        # ------------------------------------------------------------------
        # 3. Test Profile (/auth/me) with Authenticated Session
        # ------------------------------------------------------------------
        print("4. Testing GET /auth/me with session Bearer token...")
        me_res = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {login_data['token']}"},
        )
        assert me_res.status_code == 200, f"Profile fetch failed: {me_res.text}"
        profile = me_res.json()
        assert profile["email"] == test_email
        assert profile["daily_limit"] == 10
        print(f"   ✓ User profile authenticated. Free daily limit: {profile['daily_limit']}")

        # ------------------------------------------------------------------
        # 4. Test Session Refresh (/auth/refresh)
        # ------------------------------------------------------------------
        print("5. Testing POST /auth/refresh...")
        refresh_res = await client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {login_data['token']}"},
        )
        assert refresh_res.status_code == 200, f"Refresh failed: {refresh_res.text}"
        refresh_data = refresh_res.json()
        assert refresh_data["expires_in_days"] == 7
        assert refresh_data["session_id"] != login_data["session_id"], "Refreshed session ID should be newly generated"
        print(f"   ✓ Session refreshed! Fresh Session ID: {refresh_data['session_id']}")

        # ------------------------------------------------------------------
        # 5. Test Logout (/auth/logout)
        # ------------------------------------------------------------------
        print("6. Testing POST /auth/logout (Session Revocation)...")
        logout_res = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {refresh_data['token']}"},
        )
        assert logout_res.status_code == 200
        print("   ✓ Logout endpoint confirmed success.")

        # Confirm revoked session can no longer access /auth/me
        me_after_logout = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {refresh_data['token']}"},
        )
        assert me_after_logout.status_code == 401, f"Expected 401 after logout, got {me_after_logout.status_code}"
        print("   ✓ Confirmed: Revoked session token is rejected with 401 Unauthorized.")

        # ------------------------------------------------------------------
        # 6. Test Quota Reserve & Rollback
        # ------------------------------------------------------------------
        print("7. Testing Query Quota Reservation & Rollback...")
        user_id = profile["id"]
        before_user = await db_manager.get_user_by_id(user_id)
        before_today = before_user.get("query_count_today", 0)

        # Reserve
        reserved = await db_manager.reserve_query_slot(user_id, daily_limit=10)
        assert reserved is not None
        assert reserved["query_count_today"] == before_today + 1
        print(f"   ✓ Quota slot reserved: query_count_today is now {reserved['query_count_today']}")

        # Rollback
        rolled_back = await db_manager.rollback_query_slot(user_id)
        assert rolled_back["query_count_today"] == before_today
        print(f"   ✓ Quota slot refunded: query_count_today rolled back to {rolled_back['query_count_today']}")

        # ------------------------------------------------------------------
        # 7. Test CORS & Security Headers
        # ------------------------------------------------------------------
        print("8. Testing Security Headers & CORS on API responses...")
        cors_res = await client.options(
            "/auth/me",
            headers={
                "Origin": "https://ai-doc-analyzer-frontend.vercel.app",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert cors_res.status_code == 200
        assert cors_res.headers.get("access-control-allow-origin") == "https://ai-doc-analyzer-frontend.vercel.app"
        assert cors_res.headers.get("access-control-allow-credentials") == "true"
        print("   ✓ Vercel frontend CORS preflight succeeded with credentials!")

        # Root security headers
        root_res = await client.get("/")
        assert root_res.headers.get("x-content-type-options") == "nosniff"
        assert root_res.headers.get("x-frame-options") == "DENY"
        assert root_res.headers.get("x-xss-protection") == "1; mode=block"
        print("   ✓ Security headers verified (nosniff, DENY, XSS-Protection).")

    print("=" * 80)
    print("ALL AUTHENTICATION & SESSION VERIFICATION TESTS PASSED! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_auth_tests())

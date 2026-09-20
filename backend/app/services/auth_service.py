import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)
load_dotenv()

import secrets
import hashlib
import hmac
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from app.core.database import db_manager

JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
FREE_QUERY_LIMIT = 10
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 3

def ensure_utc(dt: datetime | str | None) -> datetime | None:
    """Safely normalizes any datetime string or naive/aware datetime object to UTC offset-aware."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            if "Z" in dt:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            elif "+" in dt or ("-" in dt[10:] if len(dt) > 10 else False):
                dt = datetime.fromisoformat(dt)
            else:
                dt = datetime.fromisoformat(dt).replace(tzinfo=timezone.utc)
        except Exception:
            return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return None

PLAN_LIMITS = {
    "free": 10,
    "day": 100,
    "month": 100,
    "year": 200,
}

PLAN_TOTAL_LIMITS = {
    "day": 100,
    "month": 500,
    "year": 2500,
}

class AuthService:
    def hash_password(self, plain_password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False

    def create_access_token(self, user_id: str, email: str) -> str:
        if not JWT_SECRET:
            raise RuntimeError("JWT_SECRET must be configured before issuing access tokens.")
        expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def decode_access_token(self, token: str) -> dict | None:
        if not JWT_SECRET:
            return None
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except Exception:
            return None

    def serialize_user(self, user: dict) -> dict:
        plan = user.get("plan", "free")
        expires_at = user.get("plan_expires_at")
        query_count = int(user.get("query_count") or 0)
        query_count_today = int(user.get("query_count_today") or 0)
        query_reset_at = user.get("query_reset_at")
        plan_query_count = int(user.get("plan_query_count") or 0)

        # Check if plan has expired
        is_pro = False
        if plan in ("day", "month", "year") and expires_at:
            exp_dt = ensure_utc(expires_at)
            if exp_dt and exp_dt > datetime.now(timezone.utc):
                is_pro = True
            else:
                plan = "free"

        daily_limit = PLAN_LIMITS.get(plan, 10)
        queries_remaining = max(0, daily_limit - query_count_today)
        from app.llm import get_model_name
        model_name = get_model_name(is_pro=is_pro)

        return {
            "id": user.get("id"),
            "email": user.get("email"),
            "full_name": user.get("full_name", ""),
            "query_count": query_count,
            "query_count_today": query_count_today,
            "daily_limit": daily_limit,
            "free_limit": 10,
            "queries_remaining": queries_remaining,
            "free_queries_remaining": queries_remaining if not is_pro else None,
            "query_reset_at": query_reset_at,
            "plan": plan,
            "plan_expires_at": expires_at,
            "plan_query_count": plan_query_count if is_pro else None,
            "plan_query_limit": PLAN_TOTAL_LIMITS.get(plan) if is_pro else None,
            "is_pro": is_pro,
            "model_name": model_name,
            "created_at": user.get("created_at"),
        }

    # ========================================================
    # OTP Generation & Delivery (Abstracted & Cryptographic)
    # ========================================================
    async def generate_and_send_otp(self, email: str, purpose: str = "login") -> dict:
        if not email or "@" not in email:
            raise ValueError("A valid email address is required.")

        normalized_email = email.strip().lower()

        # Check existing OTP for rate limiting (60 seconds)
        existing_otp = await db_manager.get_otp(normalized_email, purpose)
        if existing_otp:
            created_dt = ensure_utc(existing_otp.get("created_at"))
            if created_dt:
                diff_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
                if diff_seconds < 60:
                    wait_seconds = max(1, int(60 - diff_seconds))
                    raise ValueError(f"Please wait {wait_seconds}s before requesting a new code.")

        # Generate cryptographic 6-digit numeric OTP
        raw_otp = f"{secrets.randbelow(900000) + 100000}"
        salt = secrets.token_hex(16)
        hashed_otp = hashlib.sha256(f"{salt}:{raw_otp}".encode("utf-8")).hexdigest()

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

        await db_manager.save_otp(
            email=normalized_email,
            hashed_otp=hashed_otp,
            salt=salt,
            expires_at_iso=expires_at.isoformat(),
            purpose=purpose,
            expires_at_dt=expires_at,
        )

        # Dispatch Email: Primary via EmailJS, optional fallback to SMTP
        email_sent = await self._send_emailjs_otp(normalized_email, raw_otp, purpose)
        if not email_sent:
            smtp_sent = self._send_email_otp(normalized_email, raw_otp, purpose)
            if not smtp_sent:
                await db_manager.delete_otp(normalized_email, purpose)
                raise ValueError(
                    "Unable to dispatch verification email. Please check your EmailJS service settings or try again shortly."
                )

        return {
            "success": True,
            "message": f"A 6-digit verification code was sent to {normalized_email}.",
        }

    async def _send_emailjs_otp(self, email: str, otp: str, purpose: str = "login") -> bool:
        """
        Dispatches the 6-digit OTP code using EmailJS REST API.
        Never exposes OTP to the client or API response.
        """
        service_id = os.getenv("EMAILJS_SERVICE_ID", "").strip()
        template_id = os.getenv("EMAILJS_TEMPLATE_ID", "").strip()
        public_key = os.getenv("EMAILJS_PUBLIC_KEY", "").strip()
        private_key = os.getenv("EMAILJS_PRIVATE_KEY", "").strip()
        sender_email = os.getenv("SENDER_EMAIL", "").strip() or os.getenv("SMTP_FROM_EMAIL", "noreply@docai-analyzer.com")

        if not service_id or not template_id or not public_key:
            print("[EMAILJS WARNING] Configuration incomplete (EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, EMAILJS_PUBLIC_KEY required).")
            return False

        url = "https://api.emailjs.com/api/v1.0/email/send"
        frontend_origin = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

        headers = {
            "Content-Type": "application/json",
            "Origin": frontend_origin,
            "Referer": f"{frontend_origin}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        payload = {
            "service_id": service_id,
            "template_id": template_id,
            "user_id": public_key,
            "template_params": {
                "email": email,
                "to_email": email,
                "user_email": email,
                "recipient": email,
                "to_name": email.split("@")[0],
                "user_name": email.split("@")[0],
                "otp": otp,
                "otp_code": otp,
                "code": otp,
                "passcode": otp,
                "message": f"Your DocAI verification code is {otp}. It expires in {OTP_EXPIRY_MINUTES} minutes.",
                "sender_email": sender_email,
                "from_email": sender_email,
                "from_name": "DocAI Security",
                "app_name": "DocAI Document Analyzer",
                "expiry_minutes": str(OTP_EXPIRY_MINUTES),
            },
        }
        if private_key:
            payload["accessToken"] = private_key

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
                if resp.status_code in (200, 201):
                    print(f"[EMAILJS SUCCESS] Verification email dispatched successfully to {email}")
                    return True
                else:
                    print(f"[EMAILJS ERROR] HTTP {resp.status_code}: {resp.text}")
                    return False
        except Exception as exc:
            print(f"[EMAILJS EXCEPTION] Error dispatching email: {exc}")
            return False

    def _send_email_otp(self, email: str, otp: str, purpose: str) -> bool:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM_EMAIL", "noreply@docai-analyzer.com")

        if not smtp_host or not smtp_user:
            return False  # Silently skip if SMTP is not configured

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Your DocAI Verification Code: {otp}"
            msg["From"] = smtp_from
            msg["To"] = email

            text_body = f"Your verification code is: {otp}\nValid for 10 minutes. If you did not request this, please ignore."
            html_body = f"""
            <div style="font-family: sans-serif; max-width: 500px; padding: 24px; border: 1px solid #e5e5e5; border-radius: 8px;">
                <h2 style="color: #18181b; margin-top: 0;">DocAI Verification Code</h2>
                <p style="color: #6b6b6b; font-size: 14px;">Use the 6-digit code below to securely authenticate your session:</p>
                <div style="font-size: 32px; font-weight: 700; letter-spacing: 6px; padding: 14px 20px; background: #f4f4f5; border-radius: 6px; text-align: center; color: #18181b; margin: 20px 0;">
                    {otp}
                </div>
                <p style="color: #9a9a9a; font-size: 12px;">This code expires in 10 minutes. Never share this code with anyone.</p>
            </div>
            """
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_from, [email], msg.as_string())
            print(f"[SMTP SUCCESS] Verification email sent to {email}")
            return True
        except Exception as exc:
            print(f"[SMTP WARNING] Failed to send email to {email}: {exc}")
            return False

    # ========================================================
    # OTP Verification & Authentication
    # ========================================================
    async def verify_otp_and_authenticate(
        self,
        email: str,
        otp_code: str,
        purpose: str = "login",
        password: str | None = None,
        full_name: str = "",
    ) -> tuple[dict, str]:
        normalized_email = email.strip().lower()
        cleaned_otp = "".join(filter(str.isdigit, str(otp_code)))

        stored_otp = await db_manager.get_otp(normalized_email, purpose, prune_if_expired=False)
        if not stored_otp:
            raise ValueError("No verification code found. Please request a new code.")

        # Check expiration
        exp_dt = ensure_utc(stored_otp.get("expires_at_dt") or stored_otp.get("expires_at"))
        if exp_dt and exp_dt < datetime.now(timezone.utc):
            await db_manager.delete_otp(normalized_email, purpose)
            raise ValueError("Verification code has expired. Please request a new one.")

        # Check attempts
        attempts = stored_otp.get("attempts", 0)
        if attempts >= MAX_OTP_ATTEMPTS:
            await db_manager.delete_otp(normalized_email, purpose)
            raise ValueError("Too many failed attempts. For your security, this code was invalidated.")

        # Compare hashed OTP
        salt = stored_otp.get("salt", "")
        expected_hash = stored_otp.get("hashed_otp", "")
        computed_hash = hashlib.sha256(f"{salt}:{cleaned_otp}".encode("utf-8")).hexdigest()

        if not hmac.compare_digest(computed_hash, expected_hash):
            await db_manager.increment_otp_attempts(normalized_email, purpose)
            remaining_attempts = MAX_OTP_ATTEMPTS - (attempts + 1)
            raise ValueError(f"Invalid verification code. {remaining_attempts} attempts remaining.")

        # Delete verified OTP
        await db_manager.delete_otp(normalized_email, purpose)

        # Fetch or create user
        user = await db_manager.get_user_by_email(normalized_email)
        if not user:
            # Create user account
            pw = password if password and len(password) >= 6 else secrets.token_urlsafe(16)
            password_hash = self.hash_password(pw)
            user = await db_manager.create_user(
                email=normalized_email,
                password_hash=password_hash,
                full_name=full_name or normalized_email.split("@")[0],
            )
        else:
            # Refresh quota and initialize daily counter if needed
            user = await db_manager.check_and_refresh_quota(user["id"]) or user
            # If user already exists and provided a new password, update it
            if password and len(password) >= 6:
                user = await db_manager.update_user(user["id"], {
                    "password_hash": self.hash_password(password),
                }) or user

        token = self.create_access_token(user["id"], user["email"])
        return self.serialize_user(user), token

    # ========================================================
    # Legacy Direct Password Methods
    # ========================================================
    async def register(self, email: str, password: str, full_name: str = "") -> tuple[dict, str]:
        if not email or "@" not in email:
            raise ValueError("A valid email address is required.")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        password_hash = self.hash_password(password)
        user = await db_manager.create_user(email, password_hash, full_name)
        token = self.create_access_token(user["id"], user["email"])
        return self.serialize_user(user), token

    async def authenticate(self, email: str, password: str) -> tuple[dict, str]:
        user = await db_manager.get_user_by_email(email)
        if not user:
            raise ValueError("Invalid email or password.")

        if not self.verify_password(password, user.get("password_hash", "")):
            raise ValueError("Invalid email or password.")

        token = self.create_access_token(user["id"], user["email"])
        return self.serialize_user(user), token

    async def get_user_from_token(self, token: str) -> dict | None:
        payload = self.decode_access_token(token)
        if not payload or "sub" not in payload:
            return None

        user = await db_manager.check_and_refresh_quota(payload["sub"])
        if not user:
            return None
        return self.serialize_user(user)

auth_service = AuthService()

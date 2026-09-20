from typing import Literal

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from app.services.auth_service import auth_service
from app.core.database import db_manager
from app.core.rate_limit import rate_limiter

router = APIRouter()

class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SendOtpRequest(RequestModel):
    email: str = Field(min_length=3, max_length=254)
    purpose: Literal["login", "signup"] = "login"

class VerifyOtpRequest(RequestModel):
    email: str = Field(min_length=3, max_length=254)
    otp: str = Field(min_length=6, max_length=6)
    purpose: Literal["login", "signup"] = "login"
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=100)

class SignupRequest(RequestModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=100)

class LoginRequest(RequestModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"

async def get_current_user_optional(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        return await auth_service.get_user_from_token(token)
    return None

async def get_current_user_required(authorization: str | None = Header(default=None)) -> dict:
    user = await get_current_user_optional(authorization)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login.",
        )
    return user

@router.post("/send-otp")
async def send_otp(req: SendOtpRequest, request: Request):
    rate_limiter.check(f"otp:ip:{_client_key(request)}", limit=10, window_seconds=3600)
    rate_limiter.check(f"otp:email:{req.email.lower()}", limit=5, window_seconds=3600)
    try:
        return await auth_service.generate_and_send_otp(
            email=req.email,
            purpose=req.purpose,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to send a verification code right now.")

@router.post("/verify-otp")
async def verify_otp(req: VerifyOtpRequest, request: Request):
    rate_limiter.check(f"verify-otp:ip:{_client_key(request)}", limit=20, window_seconds=3600)
    try:
        user, token = await auth_service.verify_otp_and_authenticate(
            email=req.email,
            otp_code=req.otp,
            purpose=req.purpose,
            password=req.password,
            full_name=req.full_name,
        )
        return {
            "token": token,
            "user": user,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to verify the code right now.")

@router.post("/signup")
async def signup(req: SignupRequest, request: Request):
    rate_limiter.check(f"signup:ip:{_client_key(request)}", limit=8, window_seconds=3600)
    try:
        user, token = await auth_service.register(
            email=req.email,
            password=req.password,
            full_name=req.full_name,
        )
        return {
            "token": token,
            "user": user,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to create the account right now.")

@router.post("/login")
async def login(req: LoginRequest, request: Request):
    rate_limiter.check(f"login:ip:{_client_key(request)}", limit=20, window_seconds=900)
    rate_limiter.check(f"login:email:{req.email.lower()}", limit=10, window_seconds=900)
    try:
        user, token = await auth_service.authenticate(
            email=req.email,
            password=req.password,
        )
        return {
            "token": token,
            "user": user,
        }
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to authenticate right now.")

@router.get("/me")
async def get_profile(user: dict = Depends(get_current_user_required)):
    return user

@router.get("/history")
async def get_purchase_history(user: dict = Depends(get_current_user_required)):
    payments = await db_manager.get_user_payments(user["id"])
    return {
        "user_id": user["id"],
        "payments": payments,
    }

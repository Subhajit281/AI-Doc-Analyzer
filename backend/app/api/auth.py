from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from app.services.auth_service import auth_service
from app.core.database import db_manager

router = APIRouter()

class SendOtpRequest(BaseModel):
    email: str
    purpose: str = "login"

class VerifyOtpRequest(BaseModel):
    email: str
    otp: str
    purpose: str = "login"
    password: str | None = None
    full_name: str = ""

class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

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
async def send_otp(req: SendOtpRequest):
    try:
        return await auth_service.generate_and_send_otp(
            email=req.email,
            purpose=req.purpose,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send code: {str(exc)}")

@router.post("/verify-otp")
async def verify_otp(req: VerifyOtpRequest):
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
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to verify code: {str(exc)}")

@router.post("/signup")
async def signup(req: SignupRequest):
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
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create account: {str(exc)}")

@router.post("/login")
async def login(req: LoginRequest):
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
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to authenticate: {str(exc)}")

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

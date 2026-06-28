from fastapi import APIRouter, Depends, HTTPException, status
import psycopg2
import secrets

from app.config import settings
from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, RegisterRequest
from app.core.security import verify_password, create_access_token
from app.models.user import create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db=Depends(get_db)):
    if not settings.invite_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is not available.",
        )
    if not secrets.compare_digest(data.invite_key, settings.invite_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid register key.",
        )

    # check email not already taken
    existing = get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = create_user(db, data, role="admin")
    token = create_access_token({"sub": str(user["id"]), "role": user["role"]})
    return TokenResponse(access_token=token)

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db=Depends(get_db)):
    user = get_user_by_email(db, data.email)

    if user is None or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    token = create_access_token({
        "sub": str(user["id"]),
        "role": user["role"],
    })

    return TokenResponse(access_token=token)
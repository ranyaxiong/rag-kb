from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from app.core.config import settings
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash



router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
ph = PasswordHash.recommended()

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def require_admin(token: str = Depends(oauth2_scheme)) -> dict:
    secret = settings.get_jwt_secret()
    alg = settings.jwt_algorithm
    claims = jwt.decode(token, secret, algorithms=[alg])
    if claims["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return claims


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != settings.admin_username:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not ph.verify(form.password, settings.get_admin_password_hash()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    token = jwt.encode({
        "sub": form.username,
        "exp": exp,
        "role": "admin",
        "iat": datetime.now(timezone.utc)
    }, settings.get_jwt_secret(), algorithm=settings.jwt_algorithm)
    return TokenResponse(access_token=token)

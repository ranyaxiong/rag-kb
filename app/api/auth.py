from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt, datetime as dt


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def require_admin(token: str = Depends(oauth2_scheme)) -> dict:
    claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if claims["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return claims


@router.post("/login")

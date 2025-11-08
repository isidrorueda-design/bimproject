from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from .settings import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class TokenData(BaseModel):
    email: Optional[str] = None
    company_id: Optional[int] = None
    role: Optional[str] = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])        
        email: str = payload.get("sub")
        company_id: Optional[int] = payload.get("cid")
        role: str = payload.get("role")
        
        if email is None: # El company_id puede ser None para el super_admin
            return None 
        return TokenData(email=email, company_id=company_id, role=role)
    except JWTError:
        return None
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from . import crud, models, schemas, security
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = security.decode_access_token(token)
    if token_data is None:
        raise credentials_exception
        
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
):

    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user

async def get_current_super_admin(
    current_user: models.User = Depends(get_current_active_user)
):

    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Operación no permitida. Se requieren privilegios de Super Administrador."
        )
    return current_user

async def get_current_company_user(
    current_user: models.User = Depends(get_current_active_user)
):

    if current_user.role == "super_admin" or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Esta acción es solo para usuarios de una compañía."
        )
    return current_user

async def get_current_company_admin(
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Operación no permitida. Se requieren privilegios de Administrador."
        )
    return current_user

async def get_current_user_in_company(
    current_user: models.User = Depends(get_current_active_user)
):
    if not current_user.company_id:
        raise HTTPException(status_code=403, detail="Acción no permitida para este tipo de usuario.")
    return current_user
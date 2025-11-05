# app/security.py
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# --- Configuración de Seguridad ---
# Usaremos Passlib para el hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Clave secreta para firmar los JWT.
# ¡IMPORTANTE! Lee la clave desde una variable de entorno.
# Genera una clave segura con: openssl rand -hex 32
SECRET_KEY = os.getenv("SECRET_KEY", "un-secreto-muy-seguro-y-dificil-de-adivinar")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

if SECRET_KEY == "un-secreto-muy-seguro-y-dificil-de-adivinar":
    print("ADVERTENCIA: La SECRET_KEY es la predeterminada. Cámbiala en producción.")

# --- Funciones de Contraseña ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña plana coincide con un hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña."""
    return pwd_context.hash(password)

# --- Funciones de JWT ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un nuevo token de acceso JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Por defecto, el token expira en 15 minutos
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

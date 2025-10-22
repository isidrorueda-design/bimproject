# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .settings import DATABASE_URL

# Creamos el motor de conexión
engine = create_engine(DATABASE_URL)

# Creamos una fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para nuestros modelos (tablas)
Base = declarative_base()

# Función de dependencia para la API
# Esto manejará el ciclo de vida de la sesión:
# 1. Abre sesión al recibir request
# 2. Entrega la sesión
# 3. Cierra la sesión al terminar
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
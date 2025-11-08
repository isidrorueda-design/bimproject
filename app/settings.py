from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_PASSWORD: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    model_config = SettingsConfigDict(env_file=".env") 

settings = Settings()

DATABASE_URL = f"postgresql://contech_user:{settings.DB_PASSWORD}@localhost:5432/contech_db"
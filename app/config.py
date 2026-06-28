# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ecommerce"
    db_user: str = "postgres"
    db_password: str
    
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    invite_key: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ecommerce"
    db_user: str = "postgres"
    db_password: str

    class Config:
        env_file = ".env"

settings = Settings()
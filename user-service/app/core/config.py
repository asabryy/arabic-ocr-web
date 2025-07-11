from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "super-secret-key"

    class Config:
        env_file = ".env"

settings = Settings()

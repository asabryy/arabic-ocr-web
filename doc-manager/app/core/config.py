from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    UPLOAD_DIR: str = "./uploads"

    # JWT — must match auth-service values to verify tokens
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_url: str | None = None
    rabbitmq_queue: str = "ocr_tasks"
    rabbitmq_user: str = "guest"
    rabbitmq_pass: str = "guest"
    rabbitmq_uri: str | None = None

    # OCR service
    ocr_service_url: str = "http://localhost:8002/ocr"

    # Storage
    STORAGE_BACKEND: str = "local"

    # Cloudflare R2 — optional, only required when STORAGE_BACKEND=r2
    R2_ENDPOINT_URL: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""

    # CORS — comma-separated list of allowed origins
    CORS_ORIGINS: list[str] = [
        "https://textara.netlify.app",
        "https://textara.app",
        "https://www.textara.app",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()

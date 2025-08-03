from pydantic_settings import BaseSettings
from pydantic import AnyUrl, Field

class Settings(BaseSettings):
    UPLOAD_DIR: str = Field(..., env="UPLOAD_DIR")
    rabbitmq_host: str = Field(default="localhost", env="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, env="RABBITMQ_PORT")
    rabbitmq_url: str | None = Field(default=None, env="RABBITMQ_URL")
    rabbitmq_queue: str = Field(default="ocr_tasks", env="RABBITMQ_QUEUE")

    ocr_service_url: AnyUrl = Field(default="http://localhost:8001/ocr", env="OCR_SERVICE_URL")

    s3_bucket: str = Field(..., env="S3_BUCKET")
    s3_region: str = Field(..., env="S3_REGION")
    s3_endpoint: AnyUrl = Field(..., env="S3_ENDPOINT")
    s3_access_key: str = Field(..., env="S3_ACCESS_KEY")
    s3_secret_key: str = Field(..., env="S3_SECRET_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

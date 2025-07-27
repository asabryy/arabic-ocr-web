from pydantic-settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Doc Manager"

    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"
    RABBITMQ_QUEUE: str = "doc_tasks"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

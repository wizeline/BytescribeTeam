from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Bytescribe application"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["*"]


settings = Settings()

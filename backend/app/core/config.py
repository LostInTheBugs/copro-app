from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "CoproApp"
    database_url: str = "sqlite:///./copro.db"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 30
    upload_dir: str = "./uploads"
    frontend_dist: str = ""
    model_config = {"env_prefix": "COPRO_", "env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

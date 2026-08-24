from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "CoproApp"
    database_url: str = "sqlite:///./copro.db"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 30
    upload_dir: str = "./uploads"
    upload_max_mb: float = 25.0
    frontend_dist: str = ""
    # Origines CORS autorisées (JSON dans l'environnement, ex. '["https://app.example.fr"]').
    # Vide en production : le frontend est servi par le même backend, le CORS ne sert à rien.
    cors_origins: list[str] = []
    model_config = {"env_prefix": "COPRO_", "env_file": ".env"}

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Garde-fou : ne jamais signer les JWT avec la clé publique par défaut hors dev SQLite.
    if s.secret_key == "change-me" and not s.is_sqlite:
        raise RuntimeError(
            "COPRO_SECRET_KEY n'est pas définie (valeur par défaut 'change-me'). "
            "Définissez la variable d'environnement COPRO_SECRET_KEY avec une clé "
            "aléatoire avant de démarrer sur une base non-SQLite."
        )
    return s

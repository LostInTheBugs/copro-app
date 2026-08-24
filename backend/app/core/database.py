from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# NOTE — migrations :
# Le schéma est géré par Alembic (backend/alembic/, commande `alembic upgrade head`).
# L'ancien init_db() (create_all + _MIGRATIONS) a été supprimé : ne jamais
# recréer de create_all au démarrage — voir README (section Déploiement).

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


def init_db():
    import app.models  # noqa: F401 — enregistre tous les modèles
    Base.metadata.create_all(bind=engine)
    migrate()


# Migrations légères sans alembic : ajoute les colonnes manquantes
# (compatible SQLite et PostgreSQL).
_MIGRATIONS = [
    ("ags", "heure", "VARCHAR DEFAULT ''"),
    ("coproprietes", "smtp_host", "VARCHAR DEFAULT ''"),
    ("coproprietes", "smtp_port", "INTEGER DEFAULT 587"),
    ("coproprietes", "smtp_user", "VARCHAR DEFAULT ''"),
    ("coproprietes", "smtp_password", "VARCHAR DEFAULT ''"),
    ("coproprietes", "email_expediteur", "VARCHAR DEFAULT ''"),
    ("coproprietes", "frontend_url", "VARCHAR DEFAULT ''"),
]


def migrate():
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    for table, column, coltype in _MIGRATIONS:
        if table not in insp.get_table_names():
            continue
        cols = {c["name"] for c in insp.get_columns(table)}
        if column not in cols:
            with engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {coltype}'))

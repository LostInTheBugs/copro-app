FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic

RUN mkdir -p /app/uploads /app/frontend_dist

EXPOSE 8000
# Migration explicite au démarrage du conteneur, avant le serveur :
# `alembic upgrade head` est idempotent, une seule instance backend tourne
# (compose actuel) — voir README, section Déploiement.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

"""Tests du durcissement configuration & authentification (tâche 02).

Couvre les points 1 (secret_key), 2 (fallback copro), 3 (scope des users)
demandés, plus les points 6 (upload) et 7 (rate limiting) qui sont bon marché.

Note : fichier AUTONOME (fixtures locales) — il ne dépend pas du conftest de
la branche fix/isolation-multicopro (non mergée). Quand les deux branches
seront mergées, ces fixtures locales shadowent celles du conftest sans conflit.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["COPRO_DATABASE_URL"] = "sqlite://"
os.environ["COPRO_UPLOAD_DIR"] = tempfile.mkdtemp(prefix="copro-tests-uploads-")

from app import models  # noqa: E402, F401 — enregistre tous les modèles
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.copropriete import Copropriete  # noqa: E402
from app.models.user import User, UserCopro  # noqa: E402


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db(db_engine):
    session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)()
    yield session
    session.close()


@pytest.fixture()
def client(db_engine):
    TestingSession = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)

    def override_get_db():
        test_db = TestingSession()
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_syndic(db, email: str, copro: Copropriete) -> User:
    user = User(email=email, password_hash=hash_password("test1234"),
                nom=f"Syndic {email}", role="syndic", copropriete_id=copro.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(UserCopro(user_id=user.id, copropriete_id=copro.id, principale=True))
    db.commit()
    return user


@pytest.fixture()
def copro_a(db):
    c = Copropriete(nom="Résidence A")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture()
def copro_b(db):
    c = Copropriete(nom="Résidence B")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture()
def syndic_a(db, copro_a):
    return _make_syndic(db, "syndic.a@test.fr", copro_a)


@pytest.fixture()
def syndic_b(db, copro_b):
    return _make_syndic(db, "syndic.b@test.fr", copro_b)


@pytest.fixture()
def token_a(syndic_a, copro_a):
    return create_access_token(syndic_a.id, copro_a.id)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- Point 1 : clé de signature JWT ----------
def test_secret_key_defaut_refusee_hors_sqlite(monkeypatch):
    """Démarrage refusé si secret_key == 'change-me' sur une base non-SQLite."""
    from app.core.config import get_settings
    monkeypatch.setenv("COPRO_DATABASE_URL", "postgresql://user:pass@db.example.fr/copro")
    monkeypatch.setenv("COPRO_SECRET_KEY", "change-me")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="COPRO_SECRET_KEY"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_secret_key_defaut_toleree_en_dev_sqlite(monkeypatch):
    """Dev SQLite : la clé par défaut reste tolérée (pas de blocage local)."""
    from app.core.config import get_settings
    monkeypatch.setenv("COPRO_DATABASE_URL", "sqlite:///./copro.db")
    monkeypatch.setenv("COPRO_SECRET_KEY", "change-me")
    get_settings.cache_clear()
    try:
        assert get_settings().secret_key == "change-me"
    finally:
        get_settings.cache_clear()


# ---------- Point 2 : fallback copro ----------
def test_user_sans_lien_ne_recupere_pas_la_premiere_copro(client, db, copro_a):
    """Un compte sans liaison ne doit JAMAIS hériter de la première copro existante."""
    user_b = User(email="sans.lien@test.fr", password_hash=hash_password("x"),
                  nom="Sans lien", role="syndic")
    db.add(user_b)
    db.commit()
    db.refresh(user_b)
    # Token SANS copro_id (premier login)
    token_b = create_access_token(user_b.id)

    r = client.get("/api/copro", headers=auth(token_b))
    assert r.status_code == 200
    assert r.json()["id"] != copro_a.id, "l'utilisateur a hérité de la copro de A !"
    assert r.json()["nom"] == "Ma copropriété"

    liens = db.query(UserCopro).filter(UserCopro.user_id == user_b.id).all()
    assert len(liens) == 1
    assert liens[0].copropriete_id == r.json()["id"]


def test_premier_login_base_vide_cree_copro(client, db):
    """Comportement « premier login » conservé : base vide → copro neuve."""
    user = User(email="premier@test.fr", password_hash=hash_password("x"),
                nom="Premier", role="syndic")
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    r = client.get("/api/copro", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["nom"] == "Ma copropriété"
    assert db.query(Copropriete).count() == 1


# ---------- Point 3 : routes users scopées ----------
def test_list_users_scopes(client, db, copro_a, copro_b, syndic_a, syndic_b, token_a):
    membre_a = User(email="membre.a@test.fr", password_hash=hash_password("x"),
                    nom="Membre A", role="membre", copropriete_id=copro_a.id)
    db.add(membre_a)
    db.commit()
    db.refresh(membre_a)
    db.add(UserCopro(user_id=membre_a.id, copropriete_id=copro_a.id, principale=True))
    db.commit()

    r = client.get("/api/auth/users", headers=auth(token_a))
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert "syndic.a@test.fr" in emails
    assert "membre.a@test.fr" in emails
    assert "syndic.b@test.fr" not in emails, "le compte de B fuite dans la liste de A"


def test_delete_user_scopes(client, db, copro_a, copro_b, syndic_a, syndic_b, token_a):
    # A ne peut pas supprimer un compte de B (ni un id inexistant) → 404
    assert client.delete(f"/api/auth/users/{syndic_b.id}", headers=auth(token_a)).status_code == 404
    assert client.delete("/api/auth/users/99999", headers=auth(token_a)).status_code == 404
    # Garde-fou conservé : impossible de supprimer son propre compte
    assert client.delete(f"/api/auth/users/{syndic_a.id}", headers=auth(token_a)).status_code == 400

    # A peut supprimer un membre de sa copro
    membre_a = User(email="membre2.a@test.fr", password_hash=hash_password("x"),
                    nom="Membre A2", role="membre", copropriete_id=copro_a.id)
    db.add(membre_a)
    db.commit()
    db.refresh(membre_a)
    db.add(UserCopro(user_id=membre_a.id, copropriete_id=copro_a.id, principale=True))
    db.commit()
    assert client.delete(f"/api/auth/users/{membre_a.id}", headers=auth(token_a)).status_code == 200


# ---------- Point 6 : upload documents ----------
def test_upload_extension_refusee(client, token_a):
    files = {"fichier": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")}
    r = client.post("/api/documents", data={"categorie": "autre", "libelle": "Pirate"},
                    files=files, headers=auth(token_a))
    assert r.status_code == 400
    assert "Type de fichier refusé" in r.text


def test_upload_taille_limitee(client, token_a, monkeypatch):
    from app.routes import documents as docs
    monkeypatch.setattr(docs.settings, "upload_max_mb", 0.001)  # ~1 Ko
    files = {"fichier": ("gros.pdf", b"x" * 5000, "application/pdf")}
    r = client.post("/api/documents", data={"categorie": "autre", "libelle": "Gros"},
                    files=files, headers=auth(token_a))
    assert r.status_code == 413
    assert "trop volumineux" in r.text


# ---------- Point 7 : rate limiting login ----------
def test_login_rate_limited(client, db, copro_a, syndic_a):
    from app.core import rate_limit
    rate_limit._failures.clear()
    try:
        for _ in range(5):
            r = client.post("/api/auth/login", json={"email": "syndic.a@test.fr", "password": "mauvais"})
            assert r.status_code == 401
        # 6e tentative : même avec le bon mot de passe → 429
        r = client.post("/api/auth/login", json={"email": "syndic.a@test.fr", "password": "test1234"})
        assert r.status_code == 429
        assert "Trop de tentatives" in r.text
    finally:
        rate_limit._failures.clear()


def test_login_succes_efface_les_echecs(client, db, copro_a, syndic_a):
    from app.core import rate_limit
    rate_limit._failures.clear()
    try:
        r = client.post("/api/auth/login", json={"email": "syndic.a@test.fr", "password": "mauvais"})
        assert r.status_code == 401
        r = client.post("/api/auth/login", json={"email": "syndic.a@test.fr", "password": "test1234"})
        assert r.status_code == 200
        # Les échecs sont effacés après succès
        assert len(rate_limit._failures) == 0
    finally:
        rate_limit._failures.clear()

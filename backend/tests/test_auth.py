"""Authentification — register fermé, login, switch-copro, expiration de token."""
from tests.conftest import auth, _make_syndic
from app.models.user import User, UserCopro
from app.core.security import hash_password, create_access_token


def test_register_premier_compte_ok(client):
    r = client.post("/api/auth/register", json={
        "email": "premier@test.fr", "password": "test1234", "nom": "Premier",
    })
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_register_ferme_apres_premier_compte_non_demo(client, db, copro_a):
    _make_syndic(db, "syndic.a@test.fr", copro_a)  # compte non-démo existant
    r = client.post("/api/auth/register", json={
        "email": "second@test.fr", "password": "test1234", "nom": "Second",
    })
    assert r.status_code == 403
    assert "Inscription fermée" in r.text


def test_register_reste_ouvert_avec_compte_demo(client, db, copro_a):
    """Un compte démo ne ferme pas l'inscription (is_demo)."""
    demo = User(email="demo@test.fr", password_hash=hash_password("demo"),
                nom="Demo", role="syndic", is_demo=True, copropriete_id=copro_a.id)
    db.add(demo)
    db.commit()
    r = client.post("/api/auth/register", json={
        "email": "premier@test.fr", "password": "test1234", "nom": "Premier",
    })
    assert r.status_code == 200, r.text


def test_login_ok_et_mauvais_mdp(client, syndic_a):
    r = client.post("/api/auth/login", json={"email": "syndic.a@test.fr", "password": "test1234"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    r = client.post("/api/auth/login", json={"email": "syndic.a@test.fr", "password": "mauvais"})
    assert r.status_code == 401
    # Email insensible à la casse
    r = client.post("/api/auth/login", json={"email": "  SYNDIC.A@TEST.FR ", "password": "test1234"})
    assert r.status_code == 200


def test_switch_copro(client, db, copro_a, copro_b):
    _make_syndic(db, "multi@test.fr", copro_a)
    user = db.query(User).filter(User.email == "multi@test.fr").first()
    db.add(UserCopro(user_id=user.id, copropriete_id=copro_b.id, principale=False))
    db.commit()
    token = create_access_token(user.id, copro_a.id)

    # Bascule vers B
    r = client.post(f"/api/auth/switch-copro/{copro_b.id}", headers=auth(token))
    assert r.status_code == 200
    token_b = r.json()["access_token"]
    r = client.get("/api/copro", headers=auth(token_b))
    assert r.status_code == 200
    assert r.json()["id"] == copro_b.id

    # Bascule vers une copro non liée → 403
    r = client.post(f"/api/auth/switch-copro/{copro_b.id + 999}", headers=auth(token))
    assert r.status_code == 403


def test_token_expire(client, syndic_a, copro_a, monkeypatch):
    import app.core.security as security
    monkeypatch.setattr(security.settings, "access_token_expire_minutes", -1)
    token = security.create_access_token(syndic_a.id, copro_a.id)
    r = client.get("/api/auth/me", headers=auth(token))
    assert r.status_code == 401
    assert "expiré" in r.text.lower() or "invalide" in r.text.lower()


def test_token_falsifie_rejete(client, syndic_a, copro_a):
    token = create_access_token(syndic_a.id, copro_a.id)
    # Altération du payload (signature invalide)
    fake = token[:-4] + "AAAA"
    r = client.get("/api/auth/me", headers=auth(fake))
    assert r.status_code == 401

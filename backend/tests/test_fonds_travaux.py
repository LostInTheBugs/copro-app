"""Fonds de travaux — taux minimum légal de 5 % (loi ALUR)."""
from tests.conftest import auth
from app.services.country_rules import regles_fonds_travaux


def test_taux_minimum_legal_5_pct():
    regles = regles_fonds_travaux(None)
    assert regles["obligatoire"] is True
    assert regles["taux_minimum_pct"] == 5.0
    assert "5 %" in regles["texte"]


def test_api_appel_inclut_5_pct_par_defaut(client, token_a):
    """La copro par défaut a fonds_travaux_actif=True et taux 5 %."""
    r = client.post("/api/lots", json={"numero": "1", "tantiemes": 1000}, headers=auth(token_a))
    assert r.status_code == 200
    r = client.post("/api/exercices", json={"annee": 2026}, headers=auth(token_a))
    ex = r.json()
    r = client.post(f"/api/exercices/{ex['id']}/appels", json={
        "libelle": "Appel avec FT", "date_emission": "2026-01-05",
        "montant_total": 1000.0, "inclut_fonds_travaux": True,
    }, headers=auth(token_a))
    assert r.status_code == 200, r.text
    appel = r.json()
    assert abs(appel["fonds_travaux_montant"] - 50.0) < 0.01  # 5 % de 1000
    assert abs(appel["parts"][0]["montant_fonds_travaux"] - 50.0) < 0.01


def test_api_appel_sans_fonds_travaux_zero(client, token_a):
    r = client.post("/api/lots", json={"numero": "1", "tantiemes": 1000}, headers=auth(token_a))
    assert r.status_code == 200
    r = client.post("/api/exercices", json={"annee": 2026}, headers=auth(token_a))
    ex = r.json()
    r = client.post(f"/api/exercices/{ex['id']}/appels", json={
        "libelle": "Appel simple", "date_emission": "2026-01-05",
        "montant_total": 1000.0, "inclut_fonds_travaux": False,
    }, headers=auth(token_a))
    assert r.status_code == 200, r.text
    appel = r.json()
    assert appel["fonds_travaux_montant"] == 0.0
    assert appel["parts"][0]["montant_fonds_travaux"] == 0.0

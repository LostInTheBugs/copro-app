"""Solde par lot (/api/lots/soldes) — appels, encaissements, soldes négatifs."""
from tests.conftest import auth


def _setup(client, token_a, lots=(("1", 280), ("2", 260), ("3", 240), ("4", 220))):
    for num, tant in lots:
        r = client.post("/api/lots", json={"numero": num, "tantiemes": tant}, headers=auth(token_a))
        assert r.status_code == 200, r.text
    r = client.post("/api/exercices", json={"annee": 2026}, headers=auth(token_a))
    ex = r.json()
    r = client.post(f"/api/exercices/{ex['id']}/appels", json={
        "libelle": "Appel Q1", "date_emission": "2026-01-05", "montant_total": 3000.0,
    }, headers=auth(token_a))
    assert r.status_code == 200, r.text
    appel = r.json()
    return ex, appel


def test_soldes_nominal(client, token_a):
    ex, appel = _setup(client, token_a)
    lot1 = appel["parts"][0]["lot_id"]
    lot2 = appel["parts"][1]["lot_id"]

    # lot 1 paie tout (840), lot 2 paie partiellement (500)
    for lot_id, montant in ((lot1, 840.0), (lot2, 500.0)):
        r = client.post(f"/api/exercices/{ex['id']}/mouvements", json={
            "date": "2026-01-15", "libelle": "Virement", "type": "encaissement",
            "categorie": "charges", "montant": montant, "lot_id": lot_id,
        }, headers=auth(token_a))
        assert r.status_code == 200, r.text

    r = client.get("/api/lots/soldes", headers=auth(token_a))
    assert r.status_code == 200
    soldes = {s["lot"]["id"]: s for s in r.json()}

    s1 = soldes[lot1]
    assert abs(s1["total_appels"] - 840.0) < 0.01
    assert abs(s1["total_encaisse"] - 840.0) < 0.01
    assert abs(s1["solde"]) < 0.01  # tout payé

    s2 = soldes[lot2]
    assert abs(s2["total_appels"] - 780.0) < 0.01
    assert abs(s2["total_encaisse"] - 500.0) < 0.01
    assert abs(s2["solde"] - 280.0) < 0.01  # reste dû


def test_solde_negatif_credit(client, token_a):
    """Un lot qui paie plus que ses appels a un solde négatif (crédit)."""
    ex, appel = _setup(client, token_a)
    lot1 = appel["parts"][0]["lot_id"]

    r = client.post(f"/api/exercices/{ex['id']}/mouvements", json={
        "date": "2026-01-15", "libelle": "Virement", "type": "encaissement",
        "categorie": "charges", "montant": 1000.0, "lot_id": lot1,  # 840 appelé, 1000 payé
    }, headers=auth(token_a))
    assert r.status_code == 200, r.text

    r = client.get("/api/lots/soldes", headers=auth(token_a))
    s1 = {s["lot"]["id"]: s for s in r.json()}[lot1]
    assert s1["solde"] < 0
    assert abs(s1["solde"] + 160.0) < 0.01  # 840 - 1000 = -160


def test_solde_sans_appel_ni_mouvement(client, token_a):
    r = client.post("/api/lots", json={"numero": "1", "tantiemes": 1000}, headers=auth(token_a))
    assert r.status_code == 200
    r = client.get("/api/lots/soldes", headers=auth(token_a))
    assert r.status_code == 200
    s = r.json()[0]
    assert s["total_appels"] == 0.0 and s["total_encaisse"] == 0.0 and s["solde"] == 0.0

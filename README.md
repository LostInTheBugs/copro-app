# CoproApp

Gestion de copropriété pour syndic bénévole, conçue pour le régime « petite copropriété »
français (art. 41-8 de la loi du 10 juillet 1965, issu de l'ordonnance n° 2019-1101 :
**≤ 5 lots** à usage de logements, bureaux ou commerces, **ou** budget prévisionnel moyen
**< 15 000 €**/an) et **utilisable sans limite de lots** — 12 lots, 15 lots ou plus :
comptabilité simplifiée, consultation écrite, majorités de vote automatiques.

## Fonctionnalités

- **Immeuble & lots** : lots, tantièmes (millièmes), propriétaires, locataires
- **Comptabilité simplifiée** : budget prévisionnel, appels de fonds automatiques par tantièmes,
  encaissements / dépenses, solde par lot, état daté, quittances
- **Fonds de travaux** : taux configurable (min. légal 5 %), suivi dédié
- **Assemblées générales** : convocations, résolutions, moteur de majorités légal
  (art. 24 / 25 / 26, unanimité, régime 2 copropriétaires), procès-verbaux
- **Consultation écrite** (régime petite copropriété, unanimité)
- **Documents** : contrats, devis, factures, diagnostics (stockage local)
- **Carnet d'entretien** : interventions, prestataires, coûts
- **Exports** : registre des copropriétés, compte de gestion annuel
- **Multi-pays** : module de règles par pays (France en V1, extensible)

## Stack

- Backend : FastAPI + SQLAlchemy + JWT (Python 3.11)
- Frontend : React + TypeScript + Vite + Tailwind
- Base de données : PostgreSQL (prod) / SQLite (dev)
- Déploiement : Docker Compose + Caddy (TLS auto) — hébergé sur serveur

## Développement local

```bash
# Backend (port 8000)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (port 5173)
cd frontend
npm install
npm run dev
```

Premier lancement : créer le compte syndic via `POST /api/auth/register` (ouvert tant qu'aucun utilisateur n'existe).

## Déploiement (serveur)

Production : **https://copro.cloudfr.net** (Cloudflare proxy → serveur [IP], Caddy TLS Let's Encrypt).

```bash
# Sur serveur (utilisateur admin, sudo NOPASSWD pour docker)
cd /opt/copro-app
git pull                                  # mise à jour du code
# Builder le frontend sur la machine de dev puis :
tar czf - -C frontend dist | ssh serveur "cd /opt/copro-app && mkdir -p frontend_dist && tar xzf - -C frontend_dist && mv -f frontend_dist/dist/* frontend_dist/ 2>/dev/null; rmdir frontend_dist/dist 2>/dev/null"
sudo docker compose up -d --build          # rebuild backend si nécessaire
```

- `.env` (racine) : `POSTGRES_PASSWORD` + `COPRO_SECRET_KEY` (jamais commités)
- Attention : pas de `docker` sans sudo pour admin → toujours `sudo docker compose …`
- Caddy redémarre automatiquement en cas d'échec de certificat (retry 60 s)
- Mise à jour du dist frontend : copier dans `frontend_dist/` (monté en lecture seule dans le conteneur)

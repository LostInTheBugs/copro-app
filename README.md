# CoproApp

Gestion de copropriété pour syndic bénévole, conçue pour le régime « petite copropriété »
français (art. 41-8 de la loi du 10 juillet 1965, issu de l'ordonnance n° 2019-1101 :
**≤ 5 lots** à usage de logements, bureaux ou commerces, **ou** budget prévisionnel moyen
**< 15 000 €**/an) et **utilisable sans limite de lots** — 12 lots, 15 lots ou plus :
comptabilité simplifiée, consultation écrite, majorités de vote automatiques.

## 🎮 Démo

**https://copro.cloudfr.net** — un compte de démonstration est préconfiguré avec
deux copropriétés complètes (Paris : 5 lots, comptes 2024-2026, AG + PV, documents,
plan pluriannuel de travaux ; Lyon : 3 lots) :

| Champ | Valeur |
|-------|--------|
| Email | `demo@copro.cloudfr.net` |
| Mot de passe | `demo123456` |

Le compte démo ne bloque pas l'inscription : le premier compte réel peut toujours
se créer normalement depuis la page de connexion.

## Fonctionnalités

- **Immeuble & lots** : lots, tantièmes (millièmes), propriétaires, locataires
- **Comptabilité simplifiée** : budget prévisionnel, appels de fonds automatiques par tantièmes,
  encaissements / dépenses, solde par lot, état daté, quittances
- **Fonds de travaux** : taux configurable (min. légal 5 %), suivi dédié
- **Assemblées générales** : convocations, résolutions, moteur de majorités légal
  (art. 24 / 25 / 26, unanimité, régime 2 copropriétaires), procès-verbaux
- **Consultation écrite** (régime petite copropriété, unanimité)
- **Documents** : contrats, devis, factures, diagnostics (stockage local)
- **Contacts** : annuaire des entreprises, fournisseurs et artisans (téléphone, email,
  adresse, site web), recherche, catégories
- **Contrats** : énergie (EDF…), assurance copro, entretien — montant, période,
  renouvellement automatique, fournisseur lié, **échéances suivies automatiquement**
  (alertes J-60, badges Expiré / Expire bientôt, tri par urgence)
- **Carnet d'entretien** : interventions, prestataires, coûts
- **Exports** : registre des copropriétés, compte de gestion annuel
- **Multi-copropriétés** : un compte, plusieurs immeubles isolés, vue consolidée
- **Multi-pays** : module de règles par pays (France en V1, extensible)

## Stack

- Backend : FastAPI + SQLAlchemy + JWT (Python 3.11)
- Frontend : React + TypeScript + Vite + Tailwind
- Base de données : PostgreSQL (prod) / SQLite (dev)
- Déploiement : Docker Compose + Caddy (TLS auto) — hébergé sur un serveur dédié, derrière Cloudflare

## Développement local

```bash
# Backend (port 8000)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head            # crée/met à jour le schéma (SQLite dev)
uvicorn app.main:app --reload --port 8000

# Frontend (port 5173)
cd frontend
npm install
npm run dev
```

Premier lancement : créer le compte syndic via `POST /api/auth/register` (ouvert tant qu'aucun utilisateur n'existe).

## Sécurité

- **`COPRO_SECRET_KEY` obligatoire hors dev** : le backend refuse de démarrer
  (hors base SQLite) si la clé de signature JWT n'a pas été définie —
  la valeur par défaut `change-me` est publique et permettrait de forger des
  tokens. Génération : `python -c "import secrets; print(secrets.token_hex(32))"`.
- **Rate limiting sur `/api/auth/login`** : 5 tentatives échouées par email et
  par IP sur 15 minutes, puis `429` (limiteur en mémoire, adapté à une instance
  mono-serveur).
- **Upload de documents** : plafond configurable `COPRO_UPLOAD_MAX_MB` (défaut
  25 Mo, `413` au-delà) et liste blanche d'extensions
  (`.pdf .jpg .jpeg .png .doc .docx .xls .xlsx .odt .ods`, `400` sinon).
- **CORS** : liste d'origines configurable `COPRO_CORS_ORIGINS` (JSON).
  Vide en production — le frontend est servi par le même backend. En dev
  (SQLite), `http://localhost:5173` est autorisé automatiquement.
- **Isolation multi-copropriétés** : tout accès par identifiant est scopé à la
  copropriété active du token (404 si l'objet appartient à une autre copro).

## Déploiement

Production : **https://copro.cloudfr.net** (Cloudflare proxy → serveur de production, Caddy TLS Let's Encrypt).

### Migrations Alembic

Le schéma est géré par **Alembic** (`backend/alembic/`, URL lue depuis `COPRO_DATABASE_URL` —
aucune duplication dans `alembic.ini`). Les migrations tournent **explicitement**, jamais au
démarrage de l'application : le `CMD` du conteneur backend exécute `alembic upgrade head` puis
lance uvicorn (idempotent ; un seul conteneur backend dans le compose actuel).

- **Installation neuve** (nouveau serveur / base vide) : rien à faire, le conteneur migre seul.
- **Base existante créée par l'ancien `create_all` + `_MIGRATIONS`** (cas de l'instance
  actuelle) : bascule unique à faire **avant** de laisser démarrer le nouveau conteneur,
  pour marquer le schéma existant comme déjà migré sans le rejouer :

  ```bash
  cd /opt/copro-app
  git pull
  sudo docker compose build
  sudo docker compose run --rm backend sh -c "alembic stamp head"   # base existante : marquer, ne pas rejouer
  sudo docker compose up -d                                          # démarre : upgrade head = no-op + uvicorn
  ```

  Vérification : `sudo docker compose exec backend alembic current` doit afficher `head`.

- **Évolutions futures** : `alembic revision --autogenerate -m "..."` (backend/), relire la
  migration, commit, puis le déploiement l'applique au démarrage.

### Mise à jour

```bash
# Sur le serveur de production (utilisateur avec droits docker)
cd /opt/copro-app
git pull                                  # mise à jour du code
# (jusqu'à la PR docker multi-stage) : builder le frontend sur la machine de dev puis
# tar czf - -C frontend dist | ssh serveur "cd /opt/copro-app && mkdir -p frontend_dist && \
#   tar xzf - -C frontend_dist && mv -f frontend_dist/dist/* frontend_dist/ 2>/dev/null; rmdir frontend_dist/dist 2>/dev/null"
sudo docker compose up -d --build         # rebuild backend si nécessaire
```

- `.env` (racine) : `POSTGRES_PASSWORD` + `COPRO_SECRET_KEY` (jamais commités)
- Attention : pas de `docker` sans sudo pour l'utilisateur du serveur → toujours `sudo docker compose …`
- Caddy redémarre automatiquement en cas d'échec de certificat (retry 60 s)
- Mise à jour du dist frontend : copier dans `frontend_dist/` (monté en lecture seule dans le conteneur)

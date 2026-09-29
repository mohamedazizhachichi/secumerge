# SecuMerge

Plateforme légère de gestion de findings de sécurité : elle ingère les résultats de scanners externes (Semgrep, Trivy, Checkov), les normalise dans un modèle commun, les déduplique, suit leur cycle de vie et les expose via une API et un tableau de bord.

> **Statut : Étape 1 — base de données.** Le schéma (6 tables) et les migrations Alembic sont en place ; l'ingestion des rapports arrive à l'Étape 2.

## Stack

- Python 3.13 · FastAPI · Pydantic
- PostgreSQL · SQLAlchemy · Alembic *(à partir de l'Étape 1)*
- Jinja2 (HTMX optionnel) pour l'interface web
- Docker + Docker Compose pour le développement local
- GitHub Actions pour la CI/CD
- pytest pour les tests

## Prérequis

- Docker Desktop installé et démarré
- Git
- Python 3.13 (optionnel : uniquement pour le lint local ; les tests tournent dans le conteneur)

## Démarrage rapide

```powershell
# 1. Créer le fichier d'environnement local (jamais commité)
Copy-Item .env.example .env

# 2. Construire et lancer l'API + PostgreSQL
docker compose up --build

# 3. Appliquer les migrations (second terminal, pendant que ça tourne)
docker compose exec api alembic upgrade head

# 4. Vérifier (navigateur ou second terminal)
curl.exe http://localhost:8000/health
```

- Santé : http://localhost:8000/health
- Documentation interactive : http://localhost:8000/docs

Arrêter : `Ctrl+C`, puis `docker compose down`.

## Tests

```powershell
docker compose exec api pytest
```

## Migrations

```powershell
# Appliquer les migrations sur la base locale
docker compose exec api alembic upgrade head

# Créer une migration après avoir modifié un modèle
docker compose exec api alembic revision --autogenerate -m "description"
```

## Structure

```text
secumerge/
├── app/
│   ├── main.py          # point d'entrée + /health
│   ├── core/            # configuration et connexion base de données
│   └── models/          # modèles SQLAlchemy (6 tables)
├── alembic/             # migrations
├── tests/               # tests pytest
├── docs/                # spécification et planning
├── security-lab/        # (à venir) code volontairement vulnérable, isolé
├── docker-compose.yml   # api + postgres
├── Dockerfile
└── requirements.txt
```

## Documentation

- `AGENTS.md` — règles de travail et conventions
- `docs/spec-secumerge.md` — spécification complète
- `docs/planning.md` — cahier des charges et planning par étapes

## Sécurité

- `.env` contient les secrets locaux et n'est **jamais** commité ; seul `.env.example` est versionné.
- Les valeurs par défaut du fichier d'exemple sont réservées au développement local.

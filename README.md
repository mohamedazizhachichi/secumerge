# SecuMerge

Plateforme légère de gestion de findings de sécurité : elle ingère les résultats de scanners externes (Semgrep, Trivy, Checkov), les normalise dans un modèle commun, les déduplique, suit leur cycle de vie et les expose via une API et un tableau de bord.

> **Statut : Étape 5 — cycle de vie.** Un scan complet et exploitable résout automatiquement les findings disparus du même scanner et du même dépôt ; un scan partiel ne change jamais rien.

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

## Ingestion d'un rapport

```powershell
curl.exe -X POST http://localhost:8000/scans `
  -F "file=@tests/data/semgrep-example.sarif" `
  -F "project=demo" -F "repository=app-vulnerable" `
  -F "scanner=semgrep" -F "commit_sha=abc123" -F "branch=main" -F "is_complete=true"
```

- `scanner` : `semgrep`, `trivy` ou `checkov`.
- Rapport limité à 10 Mo (`413` au-delà) ; JSON invalide ou non-objet refusé (`400`).
- Le projet et le dépôt sont créés automatiquement s'ils n'existent pas.
- Le rapport brut est stocké tel quel dans `scan_executions.raw_report` (JSONB).
- Les rapports Semgrep, Trivy et Checkov sont normalisés automatiquement :
  findings créés ou mis à jour par empreinte stable, avec une occurrence par
  scan. La sévérité utilise le score CVSS (`security-severity`) quand le
  scanner le fournit, sinon le niveau SARIF.
- Un scan complet résout (`RESOLVED`) les findings du même scanner absents du
  rapport ; un scan partiel (`is_complete=false`) ou un rapport sans structure
  SARIF ne résout jamais rien.

## Structure

```text
secumerge/
├── app/
│   ├── main.py          # point d'entrée + /health
│   ├── api/             # routes HTTP (POST /scans)
│   ├── core/            # configuration et connexion base de données
│   ├── models/          # modèles SQLAlchemy (6 tables)
│   ├── ingestion/       # parseurs SARIF (Semgrep, Trivy, Checkov)
│   ├── schemas/         # schémas Pydantic de l'API
│   └── services/        # logique métier (ingestion)
├── alembic/             # migrations
├── tests/               # tests pytest + exemples de rapports
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

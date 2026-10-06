# SecuMerge

Plateforme légère de gestion de findings de sécurité : elle ingère les résultats de scanners externes (Semgrep, Trivy, Checkov), les normalise dans un modèle commun, les déduplique, suit leur cycle de vie et les expose via une API et un tableau de bord.

> **Statut : Étape 7 — Security Gate.** `GET /gate` répond PASS/FAIL pour un commit : chaque scanner attendu (Semgrep, Trivy, Checkov) doit avoir au moins un scan complet, sinon FAIL.

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

## Score de risque

Chaque finding reçoit un score 0-100, recalculé à chaque ingestion et stocké
dans `risk_assessments` avec ses ingrédients (CVSS, CWE, confiance).

| Élément | Effet |
|---|---|
| Sévérité | Base : `CRITICAL` 90, `HIGH` 70, `MEDIUM` 50, `LOW` 30, `INFO` 10 |
| CVSS (`security-severity`) | Si fourni : moyenne entre la base et `CVSS × 10` |
| Confiance | Facteur : `HIGH`/absent ×1, `MEDIUM` ×0.9, `LOW` ×0.8 |
| CWE | Information stockée, sans effet numérique |

Exemple : un CVE `CRITICAL` avec CVSS 9.8 → (90 + 98) / 2 = **94**.

## Security Gate

Verdict PASS/FAIL pour un commit : chaque scanner attendu (`semgrep`, `trivy`,
`checkov`) doit avoir au moins un scan **complet**. Un scan partiel seul ne
suffit pas et l'absence de preuve est un FAIL (fail-closed).

```powershell
curl.exe -s "http://localhost:8000/gate?project=demo&repository=app-vulnerable&commit_sha=abc123"
```

La réponse (toujours en HTTP 200) contient `status`, le détail par scanner et
la liste `missing`. Le pipeline GitHub Actions s'appuiera dessus à l'Étape 10.

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

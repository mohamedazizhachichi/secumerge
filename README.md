# SecuMerge

Plateforme légère de gestion de findings de sécurité : elle ingère les résultats de scanners externes (Semgrep, Trivy, Checkov), les normalise dans un modèle commun, les déduplique, suit leur cycle de vie et les expose via une API et un tableau de bord.

> **Statut : Étape 10 — CI GitHub Actions.** Le workflow `security.yml` scanne le dépôt à chaque push, ingère les rapports dans SecuMerge et échoue si le Security Gate ne répond pas PASS.

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

## Tableau de bord

La page d'accueil (http://localhost:8000/) affiche :

- les compteurs par sévérité et par statut ;
- la liste des findings triée par score de risque décroissant ;
- des filtres simples : sévérité, statut, scanner.

L'interface est générée côté serveur avec Jinja2 (pas de JavaScript).

## Test Lab

`security-lab/` contient des cibles volontairement vulnérables (code Python,
dépendances obsolètes, infrastructure Terraform non sécurisée) et un script
qui vérifie le pipeline de bout en bout :

```powershell
.\security-lab\run-lab.ps1
```

Le script lance les trois scanners via Docker, envoie les rapports à l'API,
contrôle les findings créés et exige un verdict **PASS** du Security Gate.
Détails dans `security-lab/README.md`.

## Intégration continue (GitHub Actions)

Le workflow `.github/workflows/security.yml` s'exécute sur chaque push vers
`main` et sur les pull requests :

1. démarre le stack (Docker Compose) et applique les migrations ;
2. lance les tests ;
3. scanne le dépôt avec Semgrep (SAST), Trivy (dépendances) et Checkov
   (Dockerfile / compose), en excluant `security-lab/` ;
4. envoie les trois rapports à `POST /scans` ;
5. échoue si `GET /gate` ne répond pas **PASS**.

Pour bloquer réellement les merges : *Settings → Branches → Add branch
protection rule* sur `main`, cocher **Require status checks to pass** et
sélectionner le job `pipeline` (workflow « security »).

## Structure

```text
secumerge/
├── app/
│   ├── main.py          # point d'entrée + /health
│   ├── api/             # routes HTTP (scans, gate, tableau de bord)
│   ├── core/            # configuration et connexion base de données
│   ├── models/          # modèles SQLAlchemy (6 tables)
│   ├── ingestion/       # parseurs SARIF (Semgrep, Trivy, Checkov)
│   ├── schemas/         # schémas Pydantic de l'API
│   ├── services/        # logique métier (ingestion, risque, gate, dashboard)
│   └── templates/       # pages Jinja2 (tableau de bord)
├── alembic/             # migrations
├── tests/               # tests pytest + exemples de rapports
├── docs/                # spécification et planning
├── security-lab/        # cibles vulnérables + script de bout en bout
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

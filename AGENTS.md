# AGENTS.md — SecuMerge

## 1. Contexte

SecuMerge est une **plateforme légère de gestion de findings de sécurité** : elle consomme les résultats de scanners externes (Semgrep, Trivy, Checkov), les normalise dans un modèle commun, déduplique, stocke leur cycle de vie, les expose via API + interface web, et s'intègre dans GitHub Actions.

- Projet personnel de fin d'études (PFE) : l'objectif est d'apprendre et de **démontrer le DevSecOps**, pas de reproduire DefectDojo ni de construire un SIEM/SOAR.
- Valeur du projet : **normalisation + agrégation + cycle de vie + visibilité + intégration DevSecOps**.
- Le reste du dossier parent (`Desktop\5eme\matiere projet\`) est le **support PFE** (deck, cahiers des charges) : ne pas y toucher depuis ce dépôt.
- Ce dépôt est **imbriqué** dans le dépôt git du profil utilisateur. Ne jamais lancer `git add -A`, `git add .` ou `git clean` depuis le home : toutes les commandes git se lancent dans `secumerge\`.

## 2. Principe de travail

**PLAN → BUILD → TEST → DOCUMENT → COMMIT.**

1. Inspecter avant de modifier : architecture, dépendances, tests, `git status`.
2. Implémenter la plus petite tranche utile.
3. Tester.
4. Mettre la documentation à jour dans le même changement.
5. Commiter.

- Jamais « construire toute la plateforme » en une seule fois.
- Pas de nouvelle dépendance sans nécessité (standard library ou existant d'abord).
- Pas d'architecture prématurée (voir les interdits ci-dessous).

## 3. Stack figée

| Domaine | Choix |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| Base de données | PostgreSQL, SQLAlchemy, Alembic |
| Frontend | Jinja2 (HTMX optionnel) — pas de React |
| Déploiement local | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Tests | pytest |
| Scanners | Semgrep (SAST), Trivy (SCA/conteneurs), Checkov (IaC) |

JSONB autorisé pour les données brutes de scanners ou métadonnées flexibles ; ne pas en abuser quand un modèle relationnel suffit.

**Interdits** sauf besoin réel démontré : Kubernetes, Kafka, Redis, Celery, Elasticsearch, microservices, bus d'événements, IA/fuzzy matching.

## 4. Structure du dépôt

```text
secumerge/
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── ingestion/
│   │   └── parsers/        # sarif.py, semgrep.py, trivy.py, checkov.py
│   ├── repositories/
│   └── templates/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── security/
├── security-lab/           # code volontairement vulnérable, isolé du vrai backend
├── docs/
├── .github/workflows/
├── alembic/
├── docker/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
└── AGENTS.md
```

Cette structure peut évoluer si l'implémentation révèle mieux ; ne pas la forcer si elle crée de la complexité inutile.

## 5. Commandes

```powershell
Copy-Item .env.example .env     # première fois uniquement (.env n'est jamais commité)
docker compose up --build       # lancer l'API + PostgreSQL
docker compose exec api alembic upgrade head    # appliquer les migrations
docker compose exec api alembic revision --autogenerate -m "..."  # nouvelle migration
docker compose exec api pytest  # tests dans le conteneur
ruff check .                    # lint (local ; sinon dans le conteneur)
docker compose down             # arrêter les services
```

## 6. Règles de sécurité non négociables

- **Secrets** : jamais commités (mots de passe, clés, tokens, identifiants). `.env` ignoré par Git, `.env.example` tenu à jour.
- **Entrées** : valider toute entrée externe (Pydantic + validation applicative).
- **Uploads** de rapports scanners : non fiables → vérifier le type, limiter la taille, parser prudemment, rejeter le malformé, ne jamais exécuter le contenu, pas de path traversal.
- **SQL** : uniquement via SQLAlchemy paramétré ; jamais de concaténation de chaînes.
- **Conteneurs** : images minimales, utilisateur non-root, versions épinglées, scan Trivy.
- **Labo vulnérable** : les vulnérabilités intentionnelles restent dans `security-lab/`, jamais dans le vrai backend.
- **CI honnête** : chaque outil a un but documenté et le pipeline échoue réellement ; pas de faux contrôle qui passe toujours.

## 7. Git

Commits courts et thématiques, préfixés :

```text
feat: ...      nouvelle fonctionnalité
fix: ...       correction
test: ...      tests
docs: ...      documentation
ci: ...        pipeline
security: ...  durcissement / correctif de sécurité
```

Jamais de commit géant mêlant des changements sans rapport.

## 8. Definition of Done

Une fonctionnalité n'est terminée que si :

- [ ] l'implémentation fonctionne en local ;
- [ ] les tests existent et passent ;
- [ ] les aspects sécurité sont traités ;
- [ ] la documentation est mise à jour ;
- [ ] `git status` est propre et le commit est clair.

## 9. Documentation de référence

- `docs/spec-secumerge.md` — spécification complète (exigences, architecture, API, sécurité, tests, phases).
- `docs/planning.md` — cahier des charges et planning par étapes (référence de planning).
- `README.md` — à construire au fil du projet (voir spec §18).

## 10. Environnement local

- Windows, PowerShell, Python 3.13, Docker Desktop.
- Le dépôt a été initialisé le 28/09/2026 (branche `main`), aucun commit initial n'est créé sans demande explicite.
